# Generated by Django 2.2.15 on 2021-08-23 13:04

import core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0005_auto_20210823_1318'),
    ]

    operations = [
        migrations.AlterField(
            model_name='associationgroup',
            name='instructions',
            field=core.fields.MarkdownTextField(blank=True, help_text='Information displayed on internal info page', max_length=2047, null=True),
        ),
    ]