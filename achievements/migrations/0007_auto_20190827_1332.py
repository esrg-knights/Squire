# Generated by Django 2.2.3 on 2019-08-27 11:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0006_auto_20190827_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='achievement',
            name='claimants',
            field=models.ManyToManyField(blank=True, to='membership_file.Member'),
        ),
    ]