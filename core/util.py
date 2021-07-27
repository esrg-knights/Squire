import logging
from functools import wraps

from django.contrib.auth.models import Permission
from django.db.models.query_utils import Q

"""
Contains various utility functions for the whole application.
"""

def suppress_warnings(function=None, logger_name='django.request'):
    """
    Decorator that surpresses Django-warnings when calling a function.
    Useful for testcases where warnings are triggered on purpose and only
    clutter the command prompt.
    Source: https://stackoverflow.com/a/46079090
    """
    def decorator(original_func):
        @wraps(original_func)
        def _wrapped_view(*args, **kwargs):
            # raise logging level to ERROR
            logger = logging.getLogger(logger_name)
            previous_logging_level = logger.getEffectiveLevel()
            logger.setLevel(logging.ERROR)

            # trigger original function that would throw warning
            original_func(*args, **kwargs)

            # lower logging level back to previous
            logger.setLevel(previous_logging_level)
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator


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
