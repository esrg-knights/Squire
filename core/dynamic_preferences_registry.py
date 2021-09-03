from core.util import get_permission_objects_from_string
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dynamic_preferences.types import ModelMultipleChoicePreference, StringPreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry

##############################################################################
# NEWSLETTER
##############################################################################

newsletter = Section('newsletter')

@global_preferences_registry.register
class NewsletterShareLink(StringPreference):
    section = newsletter
    name = 'share_link'
    verbose_name = "Public Share Link"
    description = 'A public link towards a page where anyone can view newsletters. For instance, can be a Nextcloud share URL.'
    help_text = "Leave empty to disable the newsletter page."
    default = ""
    required = False


##############################################################################
# PERMISSIONS
##############################################################################
permissions = Section('permissions')

# Permissions for everyone (including anonymous users)
DEFAULT_BASE_PERMISSIONS = ()

# Permissions for users who are logged in
DEFAULT_USER_PERMISSIONS = (
    'activity_calendar.can_view_activity_participants_during',
)

# Permissions for users who are members
DEFAULT_MEMBER_PERMISSIONS = (
    'achievements.can_view_claimants',
    'activity_calendar.can_view_activity_participants_before',
    'membership_file.can_view_membership_information_self',
    'membership_file.can_change_membership_information_self',
)

class AbstractUserTypePermission(ModelMultipleChoicePreference):
    # Obtains the default values from above
    def get_default(self):
        # Fetch permission objects based on their code (e.g., achievements.can_view_claimants)
        return get_permission_objects_from_string(self.encoded_default_permissions)

    # Alternative display method that shows the permissions in
    # human-readable format, rather than just their primary keys
    def get_default_display(self):
        return '\n'.join([str(perm) for perm in self.get_default()]) or '-'

    model = Permission
    section = permissions
    required = False
    widget = FilteredSelectMultiple("permissions", is_stacked=False)
    description = None
    help_text = _('Hold down "Control", or "Command" on a Mac, to select more than one.')


@global_preferences_registry.register
class BasePermissions(AbstractUserTypePermission):
    encoded_default_permissions = DEFAULT_BASE_PERMISSIONS
    name = 'base_permissions'
    verbose_name = 'Base Permissions'
    description = 'Permissions granted to everyone, including site visitors that are not logged in.'

@global_preferences_registry.register
class UserPermissions(AbstractUserTypePermission):
    encoded_default_permissions = DEFAULT_USER_PERMISSIONS
    name = 'user_permissions'
    verbose_name = 'User Permissions'
    description = 'Permissions granted to everyone that is logged in.'

@global_preferences_registry.register
class MemberPermissions(AbstractUserTypePermission):
    encoded_default_permissions = DEFAULT_MEMBER_PERMISSIONS
    name = 'member_permissions'
    verbose_name = 'Member Permissions'
    description = 'Permissions granted to all users that are in the membership file.'
