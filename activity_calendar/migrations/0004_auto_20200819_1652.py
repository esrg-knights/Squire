# Generated by Django 2.2.3 on 2020-08-19 14:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_presetimage'),
        ('activity_calendar', '0003_auto_20200814_1553'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='auto_create_first_slot',
            field=models.BooleanField(default=True, help_text='The first slot is automatically created if someone registers for the activity.'),
        ),
        migrations.AddField(
            model_name='activity',
            name='image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_image', to='core.PresetImage'),
        ),
        migrations.AddField(
            model_name='activityslot',
            name='image',
            field=models.ForeignKey(blank=True, help_text='If left empty, matches the image of the parent activity.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='slot_image', to='core.PresetImage'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='subscriptions_required',
            field=models.BooleanField(default=True, help_text='People are only allowed to go to the activity if they register beforehand'),
        ),
        migrations.AlterField(
            model_name='activityslot',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
