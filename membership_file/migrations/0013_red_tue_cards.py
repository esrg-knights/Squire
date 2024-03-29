# Generated by Django 2.2.24 on 2021-10-04 16:51

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0012_rename_memberlog_reverse_relations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='external_card_number',
            field=models.CharField(blank=True, help_text='External cards are blue, whereas Tu/e cards are currently red (since sept. 2021) or orange (before sept. 2021).', max_length=15, null=True, validators=[django.core.validators.RegexValidator(message='TUe card numbers must only consist of exactly 7 or 8 digits. E.g. 1234567', regex='^[0-9]{7,8}$')]),
        ),
    ]
