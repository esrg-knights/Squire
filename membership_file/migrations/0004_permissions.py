# Generated by Django 2.2.17 on 2021-07-21 09:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0003_auto_20201207_1432'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='member',
            options={'permissions': [('can_view_membership_information_self', '[F] Can view their own membership information.'), ('can_change_membership_information_self', '[F] Can edit their own membership information.')]},
        ),
        migrations.AlterField(
            model_name='member',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='member', to=settings.AUTH_USER_MODEL),
        ),
    ]
