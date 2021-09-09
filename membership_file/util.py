from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from functools import wraps


def get_member_from_user(user):
    """
    Retrieves the member associated with this user (if any)
    :param user: The user object
    :return: a Member instance or None if user has no link to a member
    """
    if user.is_authenticated:
        if hasattr(user, 'member'):
            return user.member
    return None


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
            if request.member and request.member.is_considered_member():
                return view_func(request, *args, **kwargs)

            # Otherwise show the "Not a member" error page
            resolved_fail_url = resolve_url(fail_url or settings.MEMBERSHIP_FAIL_URL)
            return HttpResponseRedirect(resolved_fail_url)
        # Wrap inside the login_required decorator (as non-logged in users can never be members)
        return login_required(_wrapped_view, login_url=login_url, redirect_field_name=redirect_field_name)

    if function:
        return decorator(function)
    return decorator

class MembershipRequiredMixin(LoginRequiredMixin):
    """
        Verifies that the current user is a member, redirecting to a special page if needed.
        Mixin-equivalent of the @membership_required decorator.
    """
    fail_url = settings.MEMBERSHIP_FAIL_URL

    def dispatch(self, request, *args, **kwargs):
        if request.member is None:
            # Current session has no member connected
            return HttpResponseRedirect(resolve_url(self.fail_url))
        if not request.member.is_considered_member():
            # Current session has a disabled member connected
            return HttpResponseRedirect(resolve_url(self.fail_url))
        return super().dispatch(request, *args, **kwargs)
