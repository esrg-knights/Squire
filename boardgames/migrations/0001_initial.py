# Generated by Django 2.2.15 on 2021-08-12 22:09

from django.db import migrations


def forwards_func(apps, schema_editor):
    # Adjust the contenttype reference
    ContentType = apps.get_model("contenttypes", "ContentType")
    db_alias = schema_editor.connection.alias
    try:
        ct = ContentType.objects.using(db_alias).get(app_label='inventory', model='boardgame')
        ct.app_label = 'boardgames'
        ct.save()
    except ContentType.DoesNotExist:
        # This content type does not exist for testcases as contenttype instances are created after migrations
        # In that case it does not matter
        pass


def reverse_func(apps, schema_editor):
    # forwards_func() creates two Country instances,
    # so reverse_func() should delete them.
    ContentType = apps.get_model("contenttypes", "ContentType")
    db_alias = schema_editor.connection.alias
    try:
        ct = ContentType.objects.using(db_alias).get(app_label='inventory', model='boardgame')
        ct.app_label = 'inventory'
        ct.save()
    except ContentType.DoesNotExist:
        # This content type does not exist for testcases as contenttype instances are created after migrations
        # In that case it does not matter
        pass



class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_auto_20210811_1539'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
