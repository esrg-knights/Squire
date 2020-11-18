from django.contrib.auth.backends import ModelBackend
from membership_file.models import MemberUser

# #####################################################################################
# Backend that provides default permissions for everyone, logged in users, and members
# TODO: Unhardcode these permissions; make them available for selection in the admin panel
# TODO: Move the permissions/"groups" to the relevant apps
# TODO: Inherit BaseBackend (which is not yet available in Django 2.2) instead of ModelBackend
# @since 03 NOV 2020
# #####################################################################################

# Permissions for everyone (including anonymous users)
base_permissions = (),

# Permissions for users who are logged in
logged_in_user_permissions = (
    'activity_calendar.can_view_activity_participants_during',
)

# Permissions for users who are members
member_permissions = (
    'achievements.can_view_claimants',
    'activity_calendar.can_view_activity_participants_before',
    'membership_file.can_view_membership_information_self',
    'membership_file.can_change_membership_information_self',
)


class BaseUserBackend(ModelBackend):
    def has_perm(self, user, perm, obj=None):
        # Permissions for everyone
        if perm in base_permissions:
            return True
        
        # Permissions for logged in users
        if user.is_authenticated and perm in logged_in_user_permissions:
            return True

        # Permissions for members
        if MemberUser(user.id).is_member() and perm in member_permissions:
            return True
        
        return False
