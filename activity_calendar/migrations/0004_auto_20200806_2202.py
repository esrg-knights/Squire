# Generated by Django 2.2.3 on 2020-08-06 20:02

from django.db import migrations
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('activity_calendar', '0003_auto_20200806_1655'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(blank=True, default=''),
        ),
    ]