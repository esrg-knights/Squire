from django.contrib.auth.models import Permission
from django.db.models.query_utils import Q

"""
Contains various utility functions for the whole application.
"""

def get_permission_objects_from_string(permission_strings):
    """
        Transform a list of permission codenames into a queryset containing those permissions.

        :param permission_strings: A collection of permissions in the form of `app_label.codename`
        :returns: A queryset of permission objects corresponding to those in the queryset.
    """
    if not permission_strings:
        return Permission.objects.none()

    q_objects = Q()
    for encoded_name in permission_strings:
        app_label, codename = encoded_name.split('.')
        q_objects |= Q(content_type__app_label=app_label, codename=codename)
    return Permission.objects.filter(q_objects)
