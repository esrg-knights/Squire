# Generated by Django 2.2.3 on 2019-08-27 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0003_auto_20190826_2225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='achievement',
            name='claimants',
            field=models.ManyToManyField(blank=True, null=True, to='membership_file.Member'),
        ),
    ]