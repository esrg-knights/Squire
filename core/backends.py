from django.contrib.auth.backends import ModelBackend
from membership_file.util import get_member_from_user

from dynamic_preferences.registries import global_preferences_registry

# #####################################################################################
# Backend that provides default permissions for everyone, logged in users, and members
# TODO: Move the permissions/"groups" to the relevant apps
# TODO: Inherit BaseBackend (which is not yet available in Django 2.2) instead of ModelBackend
# @since 03 NOV 2020
# #####################################################################################


class BaseUserBackend(ModelBackend):
    # We instantiate a manager for our global preferences
    global_preferences = global_preferences_registry.manager()

    def _in_perm_group(self, app_label, codename, group):
        return any(perm.content_type.app_label == app_label and perm.codename == codename for perm in group)

    def has_perm(self, user, perm, obj=None):
        app_label, codename = perm.split('.')

        # Permissions for everyone
        if self._in_perm_group(app_label, codename, self.global_preferences['permissions__base_permissions']):
            return True

        # Permissions for logged in users
        if user.is_authenticated \
                and self._in_perm_group(app_label, codename, self.global_preferences['permissions__user_permissions']):
            return True

        # Permissions for members
        member = get_member_from_user(user)
        if member is not None and member.is_considered_member() \
                and self._in_perm_group(app_label, codename, self.global_preferences['permissions__member_permissions']):
            return True

        return False
