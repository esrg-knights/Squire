# Generated by Django 2.2.15 on 2021-08-24 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0008_tue_card_number_length_8'),
        ('committees', '0007_auto_20210823_1626'),
    ]

    operations = [
        migrations.AlterField(
            model_name='associationgroupmembership',
            name='role',
            field=models.CharField(default='', help_text='Name of the formal role. E.g. treasurer, president', max_length=32),
        ),
        migrations.AlterField(
            model_name='associationgroupmembership',
            name='title',
            field=models.CharField(default='', help_text="Symbolic name (if any) e.g. 'God of War', 'Minister of Alien affairs', or 'Wondrous Wizard'", max_length=32),
        ),
        migrations.AlterUniqueTogether(
            name='associationgroupmembership',
            unique_together={('member', 'group')},
        ),
    ]