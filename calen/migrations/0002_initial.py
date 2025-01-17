# Generated by Django 5.0.7 on 2024-08-03 15:38

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('calen', '0001_initial'),
        ('routine', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userroutine',
            name='routine',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='routine.routine'),
        ),
        migrations.AddField(
            model_name='userroutine',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='userroutinecompletion',
            name='routine',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completions', to='calen.userroutine'),
        ),
        migrations.AddField(
            model_name='userroutinecompletion',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='userroutinecompletion',
            unique_together={('routine', 'date')},
        ),
    ]
