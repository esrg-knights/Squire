# Generated by Django 2.2.17 on 2021-07-21 09:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activity_calendar', '0006_activitymoment_locals_and_private_slot_locations'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activity',
            options={'permissions': [('can_view_activity_participants_before', "[F] Can view an activity's participants before it starts."), ('can_view_activity_participants_during', "[F] Can view an activity's participants during it."), ('can_view_activity_participants_after', "[F] Can view an activity's participants after it has ended."), ('can_register_outside_registration_period', '[F] Can (de)register for activities if registrations are closed.'), ('can_ignore_none_slot_creation_type', '[F] Can create slots for activities with slots that normally do not allow slot creation by users.'), ('can_ignore_slot_creation_limits', '[F] Can create more slots even if the maximum amount of slots is reached.'), ('can_select_slot_image', '[F] Can choose an alternative slot image when creating a slot.'), ('can_view_private_slot_locations', "[F] Can view a slot's location even if they are marked as 'private' by the activity.")], 'verbose_name_plural': 'activities'},
        ),
    ]
