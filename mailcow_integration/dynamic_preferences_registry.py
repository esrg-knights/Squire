import re
from typing import Optional
from django.apps import apps
from django.conf import settings
from dynamic_preferences.types import BooleanPreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.users.registries import user_preferences_registry

mail = Section('mail')


for alias_id, alias_data in settings.MEMBER_ALIASES.items():
    # Register user choice for each alias
    @user_preferences_registry.register
    class MemberEmailPreference(BooleanPreference):
        """ Theming of the application """
        section = mail
        name = alias_id
        default = True
        verbose_name = alias_data['description']
        description = f"Subscribed to {alias_data['address']}"
        # help_text = ''

