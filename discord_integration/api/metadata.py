from dataclasses import dataclass
from enum import Enum
import json


class DiscordMetadataTypes(Enum):
    """Application Role Connection Metadata Type"""

    # the metadata value (integer) is less than or equal to the guild's configured value (integer)
    INTEGER_LESS_THAN_OR_EQUAL = 1
    # the metadata value (integer) is greater than or equal to the guild's configured value (integer)
    INTEGER_GREATER_THAN_OR_EQUAL = 2
    # the metadata value (integer) is equal to the guild's configured value (integer)
    INTEGER_EQUAL = 3
    # the metadata value (integer) is not equal to the guild's configured value (integer)
    INTEGER_NOT_EQUAL = 4
    # the metadata value (ISO8601 string) is less than or equal to the guild's configured value (integer; days before current date)
    DATETIME_LESS_THAN_OR_EQUAL = 5
    # the metadata value (ISO8601 string) is greater than or equal to the guild's configured value (integer; days before current date)
    DATETIME_GREATER_THAN_OR_EQUAL = 6
    # the metadata value (integer) is equal to the guild's configured value (integer; 1)
    BOOLEAN_EQUAL = 7
    # the metadata value (integer) is not equal to the guild's configured value (integer; 1)
    BOOLEAN_NOT_EQUAL = 8


@dataclass
class DiscordSquireMetadata:
    """Metadata used by Discord for the purposes of Linked Roles"""

    is_active_member: bool
    is_staff: bool
    is_admin: bool
    is_honorary_member: bool

    def as_update_json(self) -> dict:
        """
        Output metadata as JSON for updating values to Discord
        NB: Discord expects boolean values as 0/1
        """
        return {
            "is_active_member": int(self.is_active_member),
            "is_staff": int(self.is_staff),
            "is_admin": int(self.is_admin),
            "is_honorary_member": int(self.is_honorary_member),
        }

    @classmethod
    def as_register_json(cls) -> str:
        """Output metadata as JSON for registration purposes in Discord"""
        return [
            {
                "key": "is_active_member",
                "name": "Active Membership",
                "description": "Has active membership in the current (academic) year.",
                "type": DiscordMetadataTypes.BOOLEAN_EQUAL.value,
            },
            {
                "key": "is_staff",
                "name": "Staff Member",
                "description": "Can login to the backend of Squire.",
                "type": DiscordMetadataTypes.BOOLEAN_EQUAL.value,
            },
            {
                "key": "is_admin",
                "name": "Administrator",
                "description": "Is a Squire administrator.",
                "type": DiscordMetadataTypes.BOOLEAN_EQUAL.value,
            },
            {
                "key": "is_honorary_member",
                "name": "Honorary Member",
                "description": "Is a honorary member. Eternal glory be upon them.",
                "type": DiscordMetadataTypes.BOOLEAN_EQUAL.value,
            },
        ]
