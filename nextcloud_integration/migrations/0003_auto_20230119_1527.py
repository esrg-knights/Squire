# Generated by Django 3.2.16 on 2023-01-19 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nextcloud_integration', '0002_alter_squirenextcloudfile_connection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='squirenextcloudfile',
            name='connection',
            field=models.CharField(choices=[('NcS', 'Synched through file on Nextcloud'), ('SqU', 'Uploaded through Squire'), ('Mnl', 'Added manually in backend')], default='Mnl', max_length=3),
        ),
        migrations.AlterUniqueTogether(
            name='squirenextcloudfile',
            unique_together={('slug', 'folder'), ('file_name', 'folder')},
        ),
    ]