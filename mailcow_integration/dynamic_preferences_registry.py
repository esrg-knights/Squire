from typing import Dict
from django.conf import settings
from django.utils.text import slugify
from django.utils.html import format_html
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import BooleanPreference
from dynamic_preferences.users.registries import user_preferences_registry

mail = Section("mail")
mailcow = Section("mailcow")


@global_preferences_registry.register
class MailcowSignalsEnabled(BooleanPreference):
    section = mailcow
    name = "mailcow_signals_enabled"
    verbose_name = "Auto-update email aliases"
    description = (
        "When enabled, email aliases are automatically updated through Django signals that connect to the Mailcow API."
    )
    default = False


def alias_address_to_id(address: str) -> str:
    """Converts an alias address to a string compatible with django-dynamic-preferences"""
    return slugify(address)


def register_preferences(member_aliases: Dict[str, Dict]):
    """Registers a user preference for each given member alias."""
    for alias_address, alias_data in member_aliases.items():
        # Register user choice for each alias
        @user_preferences_registry.register
        class MemberEmailPreference(BooleanPreference):
            """Email preferences"""

            def _get_label() -> str:
                """Gets additional text data to include in the preference's name"""
                label_elements = ["{}"]

                # Disable form field if opt-outs are disallowed
                if not alias_data["allow_opt_out"]:
                    label_elements.append(
                        '<span class="badge badge-warning badge-pill"><i class="fas fa-lock"></i> Cannot opt-out</span>'
                    )

                # Explicitly mark non-internal aliases as "public"
                if not alias_data["internal"]:
                    label_elements.append(
                        '<span class="badge badge-primary badge-pill"><i class="fas fas fa-globe"></i> Public</span>'
                    )

                # Properly escape HTML
                return format_html(
                    " ".join(label_elements),
                    alias_data["description"],
                )

            section = mail
            name = alias_address_to_id(alias_address)
            default = alias_data["default_opt"]
            verbose_name = _get_label()
            description = f"Subscribed to {alias_address}"
            # help_text = ''

            field_kwargs = {
                "disabled": not alias_data["allow_opt_out"],
            }


register_preferences(settings.MEMBER_ALIASES)
