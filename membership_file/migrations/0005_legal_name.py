# Generated by Django 2.2.17 on 2020-12-29 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0004_permissions'),
    ]

    operations = [
        # Port over the initials to the new legal_name field
        migrations.RenameField(
            model_name='member',
            old_name='initials',
            new_name='legal_name',
        ),
        migrations.AlterField(
            model_name='member',
            name='legal_name',
            field=models.CharField(default='', help_text='Legal name as known by your Educational Institution or on your ID-card.', max_length=255),
            preserve_default=False,
        ),
    ]
