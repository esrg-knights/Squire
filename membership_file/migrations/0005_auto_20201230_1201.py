# Generated by Django 2.2.17 on 2020-12-30 11:29

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0004_legal_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='state',
        ),
        migrations.AddField(
            model_name='member',
            name='external_card_deposit',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='External cards require a deposit.', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='deposit (€)'),
        ),
        migrations.AddField(
            model_name='member',
            name='has_paid_membership_fee',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='member',
            name='is_honorary_member',
            field=models.BooleanField(default=False, help_text='Honorary members can stay members forever and do not need to pay a membership fee.'),
        ),
        migrations.AddField(
            model_name='member',
            name='key_id',
            field=models.CharField(blank=True, help_text='A 4-digit code used to access the keysafe.', max_length=7, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='Key IDs consist of exaclty 4 digits. E.g. 0123', regex='^[0-9]{4}$')]),
        ),
        migrations.AddField(
            model_name='member',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='member',
            name='postal_code',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='member',
            name='preferred_pronoun',
            field=models.CharField(blank=True, help_text='This is how you will be referred to in GMM minutes.', max_length=7),
        ),
        migrations.AlterField(
            model_name='member',
            name='city',
            field=models.CharField(blank=True, default='Eindhoven', max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='country',
            field=models.CharField(default='The Netherlands', max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='educational_institution',
            field=models.CharField(blank=True, default='TU/e', max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='external_card_cluster',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='cluster'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='member',
            name='external_card_digits',
            field=models.CharField(blank=True, default='', max_length=3, validators=[django.core.validators.RegexValidator(message='External card digits must consist of exactly 3 digits. E.g. 012', regex='^[0-9]{3}$')], verbose_name='digits'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='member',
            name='first_name',
            field=models.CharField(max_length=255, verbose_name='preferred name'),
        ),
        migrations.AlterField(
            model_name='member',
            name='house_number',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='member',
            name='house_number_addition',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='addition'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='member',
            name='street',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='student_number',
            field=models.CharField(blank=True, default='', max_length=15),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='member',
            name='tussenvoegsel',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='member',
            name='country',
            field=models.CharField(blank=True, default='The Netherlands', max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='date_of_birth',
            field=models.DateField(blank=True),
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=63)),
                ('access', models.CharField(help_text="How access is provided. E.g. 'Key 12' or 'Campus Card'", max_length=15)),
                ('notes', models.TextField(blank=True)),
                ('members_with_access', models.ManyToManyField(blank=True, related_name='accessible_rooms', to='membership_file.Member')),
                ('members_with_access_removed', models.ManyToManyField(blank=True, related_name='normally_accessible_rooms', to='membership_file.Member')),
            ],
            options={
                'ordering': ['access', 'id'],
            },
        ),
    ]
