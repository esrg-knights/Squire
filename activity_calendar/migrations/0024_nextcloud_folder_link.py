# Generated by Django 3.2.16 on 2023-01-26 11:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nextcloud_integration', '0003_auto_20230119_1527'),
        ('activity_calendar', '0023_activityslot_link_to_activitymoment'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='file_folder',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='nextcloud_integration.squirenextcloudfolder'),
        ),
        migrations.AddField(
            model_name='activitymoment',
            name='local_file_folder',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='nextcloud_integration.squirenextcloudfolder'),
        ),
    ]
