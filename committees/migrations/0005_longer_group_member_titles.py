# Generated by Django 2.2.24 on 2021-09-18 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0004_auto_20210910_2036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='associationgroupmembership',
            name='title',
            field=models.CharField(blank=True, default='', help_text="Symbolic name (if any) e.g. 'God of War', 'Minister of Alien affairs', or 'Wondrous Wizard'", max_length=64),
        ),
    ]
