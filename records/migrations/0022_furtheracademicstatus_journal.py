# Generated by Django 3.2.4 on 2022-07-04 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0021_alter_student_user_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='furtheracademicstatus',
            name='journal',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
