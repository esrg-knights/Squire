from dynamic_preferences.types import ModelChoicePreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry

from membership_file.models import MemberYear

membership_section = Section("membership")


@global_preferences_registry.register
class PromoteSignUpYear(ModelChoicePreference):
    section = membership_section
    name = "signup_year"
    verbose_name = "Year for signup promotion"
    description = "The membership year that users can apply membership for"
    model = MemberYear
    default = None

    field_kwargs = {
        "required": False,
    }
