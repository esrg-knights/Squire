# Generated by Django 2.2.15 on 2021-12-31 12:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0015_auto_20211222_2102'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membership',
            name='year',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='membership_file.MemberYear'),
        ),
    ]