from dynamic_preferences.types import ChoicePreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.users.registries import user_preferences_registry

from .themes import THEMES, DEFAULT_THEME

layout = Section("layout")


@user_preferences_registry.register
class UserTheme(ChoicePreference):
    """Theming of the application"""

    section = layout
    name = "theme"
    default = DEFAULT_THEME
    choices = [(identifier, theme.name) for (identifier, theme) in THEMES.items()]
    verbose_name = "site theme"
    description = "Theme of the application"
    help_text = "Only the default theme is supported."
