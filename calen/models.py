from django.conf import settings
from django.db import models
from routine.models import Routine
from project import settings

class UserRoutine(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) #AUTH_USER_MODEL에 대한 외래키
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

class UserRoutineCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)
    routine = models.ForeignKey(UserRoutine, on_delete=models.CASCADE, related_name='completions')
    date = models.DateField()
    completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('routine', 'date') # 루틴과 조합 유일 -> 동일한 루틴에 대해 같은 날짜에 여러번 가능

class PersonalSchedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    completed = models.BooleanField(default=False)

class MonthlyTitle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.DateField()
    title = models.CharField(max_length=200)