# Generated by Django 3.2.16 on 2023-02-21 12:54

import core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activity_calendar', '0026_add_meeting_recurrence_perm'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='description',
            field=core.fields.MarkdownTextField(blank=True, help_text='Note that uploaded images are publicly accessible, even if the activity is unpublished.', null=True),
        ),
    ]
