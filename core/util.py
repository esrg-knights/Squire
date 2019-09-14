import logging
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from functools import wraps
from membership_file.models import Member


"""
Contains various utility functions for the whole application.
"""


def suppress_warnings(original_function):
    """
    Decorator that surpresses Django-warnings when calling a function.
    Useful for testcases where warnings are triggered on purpose and only
    clutter the command prompt.
    Source: https://stackoverflow.com/a/46079090
    """
    def new_function(*args, **kwargs):
        # raise logging level to ERROR
        logger = logging.getLogger('django.request')
        previous_logging_level = logger.getEffectiveLevel()
        logger.setLevel(logging.ERROR)

        # trigger original function that would throw warning
        original_function(*args, **kwargs)

        # lower logging level back to previous
        logger.setLevel(previous_logging_level)
    return new_function


def membership_required(function=None, fail_url=None):
    """
    Decorator for views that checks that the user is a member, redirecting
    to a special page if necessary.
    Based on Django's login_required and user_passes_test decorators
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and Member.objects.filter(user__id=request.user.id).exists():
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_fail_url = resolve_url(fail_url or settings.MEMBERSHIP_FAIL_URL)
            return HttpResponseRedirect(resolved_fail_url)
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator

    
    
