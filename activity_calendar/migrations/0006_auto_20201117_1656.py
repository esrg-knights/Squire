# Generated by Django 2.2.3 on 2020-11-17 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity_calendar', '0005_activitymoment_local_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='private_slot_locations',
            field=models.BooleanField(default=False, help_text='Private locations are hidden for users not registered to the relevant slot'),
        ),
        migrations.AddField(
            model_name='activitymoment',
            name='local_private_slot_locations',
            field=models.BooleanField(blank=True, choices=[('', '---------'), (True, 'Yes'), (False, 'No')], default=None, help_text='Private locations are hidden for users not registered to the relevant slot', null=True),
        ),
        migrations.AddField(
            model_name='activitymoment',
            name='local_slot_creation',
            field=models.CharField(blank=True, choices=[('CREATION_NONE', 'Never/By Administrators'), ('CREATION_AUTO', 'Automatically'), ('CREATION_USER', 'By Users')], default=None, max_length=15, null=True),
        ),
    ]
