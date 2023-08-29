from django.contrib.auth.models import Permission


def get_perm_from_name(name: str) -> Permission:
    """Gets permission object from the given name"""
    # Yeah, I'm surprised I had to write it too, but this doesn't seem to be in django.contrib.auth
    app_label, codename = name.split(".", maxsplit=1)
    return Permission.objects.get(
        content_type__app_label=app_label,
        codename=codename,
    )
