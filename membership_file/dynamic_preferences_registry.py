from dynamic_preferences.types import ModelChoicePreference, StringPreference
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


@global_preferences_registry.register
class RegistrationReplyToAddress(StringPreference):
    section = membership_section
    name = "registration_reply_to_address"
    verbose_name = "Registration Reply-To address"
    description = "The recipient address used in the “Reply-To” header when sending registration emails."
    help_text = "Leave empty to disable Reply-To. Recommended to set this to the secretary email."
    default = ""
    required = False


@global_preferences_registry.register
class RegistrationDescription(StringPreference):
    section = membership_section
    name = "registration_description"
    verbose_name = "Registration email footer description."
    description = "Description used in the footer of the registration email."
    help_text = "Recommended to set title and board number. E.g., Secretary 18th Board"
    default = ""
    required = False


@global_preferences_registry.register
class RegistrationExtraDescription(StringPreference):
    section = membership_section
    name = "registration_extra_description"
    verbose_name = "Registration email footer extra description."
    description = "Optional extra description used in the footer of the registration email."
    help_text = "Recommended to set board name. E.g., The Alliance of Alliterating Astronauts"
    default = ""
    required = False
