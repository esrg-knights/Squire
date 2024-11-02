from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from membership_file.models import Member
from membership_file.exceptions import UserIsNotCurrentMember


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


class LinkAccountTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for membership account linking.
    Mentions of "user" should instead be interpreted as "member".
    """

    # Key salt should be different from the password token generator's key salt
    key_salt = "squire.membership_file.util.LinkAccountTokenGenerator"

    def _make_hash_value(self, member: Member, timestamp: int):
        """
        Hash the members's primary key, email, and some user state
        that's sure to change after an account link to produce a token that is
        invalidated when it's used:
        1. The last_updated_date will change upon an account link.
        2. The user field will will also change upon an account link.
        Failing those things, settings.PASSWORD_RESET_TIMEOUT eventually
        invalidates the token.

        Running this data through salted_hmac() prevents account link cracking
        attempts using the reset token, provided the secret isn't compromised.
        """
        # Truncate microseconds so that tokens are consistent even if the
        # database doesn't support microseconds.
        last_updated_date = (
            "" if member.last_updated_date is None else member.last_updated_date.replace(microsecond=0, tzinfo=None)
        )
        user_id = member.user.id if member.user is not None else ""
        return f"{member.pk}{last_updated_date}{user_id}{timestamp}{member.email}"
