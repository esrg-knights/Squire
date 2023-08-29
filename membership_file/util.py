from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from functools import wraps

from membership_file.models import Member
from .exceptions import UserIsNotCurrentMember


def user_is_current_member(user):
    member = get_member_from_user(user)
    return member is not None and member.is_active


def get_member_from_user(user) -> Member:
    """
    Retrieves the member associated with this user (if any)
    :param user: The user object
    :return: a Member instance or None if user has no link to a member
    """
    if user.is_authenticated:
        if hasattr(user, "member"):
            return user.member
    return None


class BaseMembershipRequiredMixin:
    """
    Verifies that the current user is a member, redirecting to a special page if needed.
    Mixin-equivalent of the @membership_required decorator.
    """

    requires_active_membership = (
        True  # Boolean defining whether user should be active, or just linked as an (old) member
    )

    def dispatch(self, request, *args, **kwargs):
        if self.check_member_access(request.member):
            return super().dispatch(request, *args, **kwargs)
        else:
            raise UserIsNotCurrentMember()

    def check_member_access(self, member):
        if member is None:
            # Current session has no member connected
            return False
        if not member.is_active and self.requires_active_membership:
            # Current session has a disabled member connected
            return False
        return True


class MembershipRequiredMixin(LoginRequiredMixin, BaseMembershipRequiredMixin):
    pass
