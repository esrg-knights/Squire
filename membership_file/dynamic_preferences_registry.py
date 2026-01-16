from dynamic_preferences.types import ModelChoicePreference, StringPreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry

from membership_file.models import MemberYear

membership_section = Section("membership")
url_section = Section("urls")


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
class ScalaDiningLink(StringPreference):
    section = url_section
    name = "link_scala_dining"
    verbose_name = "Scala Dining link"
    description = "Link to the Scala Dining system."
    help_text = "Recommended to keep the link to the Scala Dining system up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class BuddyLink(StringPreference):
    section = url_section
    name = "link_buddy_system"
    verbose_name = "Buddy system link"
    description = "Link to sign-up for the buddy system."
    help_text = "Recommended to keep the link to the buddy system up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class WhatsAppInviteLink(StringPreference):
    section = url_section
    name = "link_invite_whatsapp"
    verbose_name = "WhatsApp invite link"
    description = "Invite link to join the WhatsApp chat."
    help_text = "Recommended to keep the link to the WhatsApp chat up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class TelegramInviteLink(StringPreference):
    section = url_section
    name = "link_invite_telegram_announcements"
    verbose_name = "Telegram Announcement invite link"
    description = "Invite link to join the Telegram Announcement chat."
    help_text = "Recommended to keep the link to the Telegram Announcements channel up-to-date"
    default = ""
    required = False


@global_preferences_registry.register
class InviteLink(StringPreference):
    section = url_section
    name = "link_invite_discord"
    verbose_name = "Discord invite link"
    description = "Invite link to join the Discord server."
    help_text = "Recommended to keep the link to the Discord server up-to-date"
    default = ""
    required = False
