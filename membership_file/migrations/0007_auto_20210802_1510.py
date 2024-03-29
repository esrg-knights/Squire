# Generated by Django 2.2.8 on 2021-08-02 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0006_more_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='notes',
            field=models.TextField(blank=True, help_text='Notes are invisible to members.'),
        ),
        migrations.AlterField(
            model_name='room',
            name='notes',
            field=models.TextField(blank=True),
        ),
    ]
