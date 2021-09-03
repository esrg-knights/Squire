# Generated by Django 2.2.15 on 2021-09-03 15:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0002_auto_20210830_1401'),
    ]

    operations = [
        migrations.AddField(
            model_name='associationgroupmembership',
            name='external_person',
            field=models.CharField(blank=True, help_text='Person not is not a member', max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='associationgroupmembership',
            name='member',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='membership_file.Member'),
        ),
    ]
