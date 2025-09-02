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


@global_preferences_registry.register
class WelcomeLetterEmail(LongStringPreference):
    section = membership_section
    name = "welcome_letter_email"
    verbose_name = "welcome letter email"
    description = "content of the welcome email members automatically get after there members file is created."
    help_text = "Recommended to keep a welcoming part for this is the meat of the email."
    default = ""
    required = False


@global_preferences_registry.register
class BuddyLink(StringPreference):
    section = membership_section
    name = "buddy_link"
    verbose_name = "Buddy link."
    description = "Place to put the link used to sign-up for the buddy system."
    help_text = "Recommended to keep the link to the buddy system up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class WhatsappLink(StringPreference):
    section = membership_section
    name = "whatsapp_link"
    verbose_name = "Whatsapp link."
    description = "Place to put the link used to join the knights Whatsapp."
    help_text = "Recommended to keep the link to the Whatsapp up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class TelegramLink(StringPreference):
    section = membership_section
    name = "telegram-announcements_link"
    verbose_name = "Telegram announcement link."
    description = "Place to put the link used to join the telegram announcement chat."
    help_text = "Recommended to keep the link to the telegram announcemnet channel up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class ScalaDiningLink(StringPreference):
    section = membership_section
    name = "scala_dining_link"
    verbose_name = "Scala Dining link."
    description = "Place to put the link to the Scala Dining system."
    help_text = "Recommended to keep the link to the Scala Dining system up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class DiscordLink(StringPreference):
    section = membership_section
    name = "discord_link"
    verbose_name = "Discord link."
    description = "Place to put the link used join the Knights Discord."
    help_text = "Recommended to keep the link to the Knights Discord up-to-date"
    default = ""
    required = False
