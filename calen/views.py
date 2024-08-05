from datetime import date, timedelta
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.db import models

from .models import UserRoutine, PersonalSchedule, MonthlyTitle, UserRoutineCompletion
from .serializers import UserRoutineSerializer, PersonalScheduleSerializer, MonthlyTitleSerializer, UserRoutineCompletionSerializer
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from routine.models import Routine
from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from datetime import datetime

from collections import defaultdict
from django.db.models import Count


class CalendarViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_user(self, request):
        user = request.user
        if not user.is_authenticated:
            return None
        return user
    
    @action(detail=False, methods=['get'])
    def daily(self, request, date=None):
        date_obj = parse_date(date)
        if not date_obj:
            return Response({"detail": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        # 개인 일정 가져오기
        schedules = PersonalSchedule.objects.filter(user=request.user, date=date_obj)
        schedule_serializer = PersonalScheduleSerializer(schedules, many=True)

        # 루틴 가져오기
        user_routines = UserRoutine.objects.filter(user=request.user, start_date__lte=date_obj, end_date__gte=date_obj)
        routine_serializer = UserRoutineSerializer(user_routines, many=True, context={'request': request, 'selected_date': date_obj})

        data = {
                'schedules': schedule_serializer.data,
                'routines': routine_serializer.data
            }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def create_schedule(self, request, date=None):
        date_obj = parse_date(date)
        if not date_obj:
            return Response({"detail": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        # 이전 날짜에 대해서는 생성 불가
        if date_obj < date.today():
            return Response({"detail": "Cannot create schedule for past dates."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        data['user'] = request.user.id
        data['date'] = date_obj

        serializer = PersonalScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'])
    def update_schedule(self, request, date=None):
        # 날짜 파싱
        date_obj = parse_date(date)
        if not date_obj:
            return Response({"detail": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        # 이전 날짜에 대해서는 수정 불가
        if date_obj < date.today():
            return Response({"detail": "Cannot update schedule for past dates."}, status=status.HTTP_400_BAD_REQUEST)

        # 요청 본문에서 필수 ID와 선택적 필드 가져오기
        schedule_id = request.data.get('id')
        if not schedule_id:
            return Response({"detail": "ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 해당 날짜와 사용자에 대한 PersonalSchedule 필터링
        schedules = PersonalSchedule.objects.filter(user=request.user, date=date_obj)

        # ID에 해당하는 스케줄 찾기
        try:
            schedule = schedules.get(id=schedule_id)
        except PersonalSchedule.DoesNotExist:
            return Response({"detail": "PersonalSchedule not found"}, status=status.HTTP_404_NOT_FOUND)

        # 업데이트할 데이터 준비
        updated_data = {}
        if 'title' in request.data:
            updated_data['title'] = request.data['title']
        if 'description' in request.data:
            updated_data['description'] = request.data['description']
        if 'completed' in request.data:
            updated_data['completed'] = request.data['completed']

        # Serializer를 사용하여 데이터 검증 및 저장
        serializer = PersonalScheduleSerializer(schedule, data=updated_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=True, methods=['post'])
    def add_routine(self, request, id=None):
        user = self.get_user(request)

        if user is None:
            return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            routine = Routine.objects.get(id=id)
        except Routine.DoesNotExist:
            return Response({'error': 'Routine not found'}, status=status.HTTP_404_NOT_FOUND)

        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({'error': 'Start date and end date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date is None or end_date is None:
                raise ValueError("Invalid date format")
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'error': 'End date must be after start date.'}, status=status.HTTP_400_BAD_REQUEST)

        # 시작일과 종료일이 오늘보다 이전이면 에러 반환
        if start_date < date.today() or end_date < date.today():
            return Response({'error': 'Cannot add routine for past dates.'}, status=status.HTTP_400_BAD_REQUEST)

        # 동일한 날짜에 동일한 루틴이 이미 존재하는지 확인
        existing_routine = UserRoutine.objects.filter(
            user=user,
            routine=routine,
            start_date__lte=start_date,
            end_date__gte=start_date
        ).exists()

        if existing_routine:
            return Response({'error': 'A routine with the same dates already exists for this user on this date.'}, status=status.HTTP_400_BAD_REQUEST)

        user_routine = UserRoutine.objects.create(
            user=user,
            routine=routine,
            start_date=start_date,
            end_date=end_date
        )

        response_data = {
            'id': routine.id,
            'status': status.HTTP_201_CREATED
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    # 어케 짤까
    # 날짜 파싱 후 월 날짜들 계산
    # 이 범위의 모든 루틴과 스케쥴 가져오기
    # 각 날짜별로 루틴과 스케쥴 완료상태 확인하고
    # for 문으로 돌려서 둘다 완료인 것만 리스트에 추가 후 정렬

    @action(detail=False, methods=['get'])
    def check_star(self, request, month=None):
        user = self.get_user(request)

        if user is None:
            return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_403_FORBIDDEN)

        if not month:
            return Response({'error': 'Month parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 월을 'YYYY-MM' 형식으로 파싱
            year, month = month.split('-')
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
            
            start_date = datetime(year, month, 1)
            end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid month format'}, status=status.HTTP_400_BAD_REQUEST)

        # 날짜 범위 내의 모든 루틴과 스케줄 가져오기
        completions = UserRoutineCompletion.objects.filter(
            user=user,
            date__range=(start_date, end_date)
        ).values('date').annotate(
            total_routines=Count('id'),
            completed_routines=Count('id', filter=Q(completed=True))
        )

        personal_schedules = PersonalSchedule.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).values('date').annotate(
            total_schedules=Count('id'),
            completed_schedules=Count('id', filter=Q(completed=True))
        )

        # 각 날짜별로 루틴과 스케줄의 완료 상태를 확인
        completed_dates_list = []
        all_dates = set([entry['date'] for entry in completions] + [entry['date'] for entry in personal_schedules])

        for date in all_dates:
            # 루틴 완료 여부 확인
            routines_for_date = next((entry for entry in completions if entry['date'] == date), None)
            routines_completed = (routines_for_date is None) or (routines_for_date['total_routines'] == routines_for_date['completed_routines'])

            # 스케줄 완료 여부 확인
            schedules_for_date = next((entry for entry in personal_schedules if entry['date'] == date), None)
            schedules_completed = (schedules_for_date is None) or (schedules_for_date['total_schedules'] == schedules_for_date['completed_schedules'])

            # 루틴과 스케줄이 모두 완료된 경우 해당 날짜를 리스트에 추가
            if routines_completed and schedules_completed:
                completed_dates_list.append(date)

        # 날짜 정렬
        completed_dates_list.sort()

        # 완료된 날짜 리스트 반환
        return Response({"completed_days": completed_dates_list})
    
class UpdateRoutineCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, date):
        try:
            user = request.user
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()

            # 이전 날짜에 대해서는 수정 불가
            if date_obj < date.today():
                return Response({"detail": "Cannot update routine completion for past dates."}, status=status.HTTP_400_BAD_REQUEST)

            routine_id = request.data.get('routine_id')
            completed = request.data.get('completed')

            if routine_id is None or completed is None:
                return Response({"detail": "Missing routine_id or completed field."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                completion = UserRoutineCompletion.objects.get(user=user, routine_id=routine_id, date=date_obj)
                completion.completed = completed
                completion.save()
            except UserRoutineCompletion.DoesNotExist:
                return Response({"detail": "UserRoutineCompletion not found."}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({"status": "Routine completion status updated successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

