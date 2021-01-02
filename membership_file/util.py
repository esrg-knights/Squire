from .models import Member, MemberUser
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from functools import wraps

def user_to_member(user):
    """
    Transforms a User to a MemberUser with the same data
    """
    # Copy over all old information
    attrs = {field.name: getattr(user, field.name) for field in user._meta.fields}
    return MemberUser(**attrs)

def request_member(function=None):
    """
    Decorator for views that transforms request.user to type MemberUser instead of User
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # Override request.user with a MemberUser with the same data
                request.user = user_to_member(request.user)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator


def membership_required(function=None, fail_url=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator for views that checks that the user is a member, redirecting
    to a special page if necessary.
    Automatically calls Django's login_required
    Based on Django's login_required and user_passes_test decorators
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):

            # If the user is authenticated and a member with the same userID exists, continue
            if request.user.is_authenticated and MemberUser(request.user.id).is_member():
                return view_func(request, *args, **kwargs)
            
            # Otherwise show the "Not a member" error page
            resolved_fail_url = resolve_url(fail_url or settings.MEMBERSHIP_FAIL_URL)
            return HttpResponseRedirect(resolved_fail_url)
        # Wrap inside the login_required decorator (as non-logged in users can never be members)
        return login_required(_wrapped_view, login_url=login_url, redirect_field_name=redirect_field_name)
    
    if function:
        return decorator(function)
    return decorator


class MembershipRequiredMixin(AccessMixin):
    """
        Verifies that the current user is a member.
        Mixin-equivalent of the membership_required decorator
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_member():
            resolved_fail_url = resolve_url(getattr(self, 'fail_url', settings.MEMBERSHIP_FAIL_URL))
            return HttpResponseRedirect(resolved_fail_url)
        return super().dispatch(request, *args, **kwargs)
