from datetime import date, timedelta
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from .models import UserRoutine, PersonalSchedule, MonthlyTitle, UserRoutineCompletion
from .serializers import UserRoutineSerializer, PersonalScheduleSerializer, MonthlyTitleSerializer, UserRoutineCompletionSerializer
from rest_framework.permissions import AllowAny

class CalendarViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # 디버깅 용도로 AllowAny 설정

    def get_user(self, request):
        user = request.user
        if isinstance(user, AnonymousUser):
            return None
        return user

    @action(detail=False, methods=['get', 'post', ''])
    def monthly(self, request, month=None):
        user = self.get_user(request)

        if user is None:
            return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_403_FORBIDDEN)

        if not month:
            return Response({'error': 'Month parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 요청된 월을 파싱하여 년과 월을 추출
            month_date = parse_date(month + "-01")
            if month_date is None:
                raise ValueError("Invalid month format")

            year = month_date.year
            month = month_date.month

            # 완료 루틴 필터링
            completed_routines = UserRoutineCompletion.objects.filter(
                user=user,
                date__year=year,
                date__month=month,
                completed=True
            )

            # completed_days 리스트 생성
            completed_days = set()

            for routine_completion in completed_routines:
                completed_days.add(routine_completion.date)

            monthly_title = MonthlyTitle.objects.filter(
                user=user,
                month__year=year,
                month__month=month
            )            

            return Response({
                'completed_days': [day.strftime('%Y-%m-%d') for day in sorted(completed_days)],
                'monthly_title': MonthlyTitleSerializer(monthly_title, many=True).data
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=False, methods=['get'])
    # def daily(self, request, date=None):
    #     user = self.get_user(request)

    #     if user is None:
    #         return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_403_FORBIDDEN)

    #     if not date:
    #         return Response({'error': 'Date parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         selected_date = parse_date(date)
    #         if selected_date is None:
    #             raise ValueError("Invalid date format")
    #     except ValueError:
    #         return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

    #     routines = UserRoutine.objects.filter(
    #         user=user,
    #         start_date__lte=selected_date,
    #         end_date__gte=selected_date,
    #     )
    #     schedules = PersonalSchedule.objects.filter(
    #         user=user,
    #         date=selected_date
    #     )

    #     # 직렬화할 때 context에 request와 selected_date를 추가
    #     serializer_context = {
    #         'request': request,
    #         'selected_date': selected_date
    #     }

    #     return Response({
    #         'date': selected_date.strftime('%Y-%m-%d'),
    #         'routines': UserRoutineSerializer(routines, many=True, context=serializer_context).data,
    #         'schedules': PersonalScheduleSerializer(schedules, many=True).data,
    #     })
        
    @action(detail=False, methods=['get', 'post', 'patch', 'delete'])
    def daily(self, request, date=None):
        user = self.get_user(request)

        if user is None:
            return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_403_FORBIDDEN)

        if not date:
            return Response({'error': 'Date parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            selected_date = parse_date(date)
            if selected_date is None:
                raise ValueError("Invalid date format")
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            routines = UserRoutine.objects.filter(
                user=user,
                start_date__lte=selected_date,
                end_date__gte=selected_date,
            )
            schedules = PersonalSchedule.objects.filter(
                user=user,
                date=selected_date
            )

            serializer_context = {
                'request': request,
                'selected_date': selected_date
            }

            return Response({
                'date': selected_date.strftime('%Y-%m-%d'),
                'routines': UserRoutineSerializer(routines, many=True, context=serializer_context).data,
                'schedules': PersonalScheduleSerializer(schedules, many=True).data,
            })

        elif request.method == 'POST':
            serializer = PersonalScheduleSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=user, date=selected_date)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'PATCH':
            try:
                schedule_id = request.data.get('id')
                schedule = PersonalSchedule.objects.get(id=schedule_id, user=user)
            except PersonalSchedule.DoesNotExist:
                return Response({'error': 'PersonalSchedule not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = PersonalScheduleSerializer(schedule, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            try:
                schedule_id = request.data.get('id')
                schedule = PersonalSchedule.objects.get(id=schedule_id, user=user)
                schedule.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except PersonalSchedule.DoesNotExist:
                return Response({'error': 'PersonalSchedule not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)