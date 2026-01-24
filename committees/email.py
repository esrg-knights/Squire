from dataclasses import dataclass, field
from enum import Enum
import json
from typing import cast
from typing_extensions import Self

from django.apps import apps
from django.db.models import QuerySet, Exists, OuterRef
from django.utils.text import slugify
from dynamic_preferences.users.models import UserPreferenceModel

from committees.apps import CommitteesConfig
from committees.models import AssociationGroup
from mailcow_integration.dynamic_preferences_registry import alias_address_to_id
from membership_file.models import Member


def get_email_settings() -> "SquireEmailManager | None":
    """Access the AppConfig to obtain Squire's Email settings."""
    return cast(CommitteesConfig, apps.get_app_config("committees")).email_manager


@dataclass
class MemberMailingListAliasSettings:
    """
    Settings for mailing lists for members.
    - `title`: Title of the mailing list
    - `description`: Description of the mailing list
    - `internal`: If true, this mailing list can only be emailed by committees and other admins.
    - `allow_opt_out`: If false, members cannot opt-out for this mailing list.
    - `default_opt`: The default opt-in status for members
    - `archive_addresses`: List of email addresses to receive a BCC when this mailing list is emailed.
    """

    title: str
    description: str
    internal: bool = True
    allow_opt_out: bool = True
    default_opt: bool = False
    archive_addresses: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, settings: dict) -> Self:
        """
        Construct an instance of this setting based on a JSON dict.

        :raise: `KeyError` when one of the setting fields is missing.
        """
        return cls(
            settings["title"],
            settings["description"],
            settings["internal"],
            settings["allow_opt_out"],
            settings["default_opt"],
            settings["archive_addresses"],
        )


@dataclass
class CommitteeEmailSettings:
    """
    Settings for aliases related to committees.
    - `receive_archive_addresses`: List of email addresses to receive a BCC when ANY committee is emailed.
    - `global_addresses`: List of email addresses that can be used to email all committees at the same time.
    - `global_archive_addresses`: List of email addresses to receive a BCC when any of the `global_addresses` addresses is emailed.
    """

    receive_archive_addresses: list[str] = field(default_factory=list)
    global_addresses: list[str] = field(default_factory=list)
    global_archive_addresses: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, settings: dict) -> Self:
        """
        Construct an instance of this setting based on a JSON dict.

        :raise: `KeyError` when one of the setting fields is missing.
        """
        return cls(
            settings["receive_archive_addresses"], settings["global_addresses"], settings["global_archive_addresses"]
        )


MemberMailingListAliases = dict[str, MemberMailingListAliasSettings]
MemberMailingListAlias = tuple[str, MemberMailingListAliasSettings]


@dataclass
class EmailAliasSettings:
    """
    Settings for email configuration used by various other modules.
    - `domains`: List of domains. The first listed domain is considered the primary domains. Should not include the @-symbol. E.g. example.com
    - `committee_settings`: Email alias configuration for committees
    - `mailing_lists`: Mailing list configuration for members
    - `primary_domain`: The primary domain. If unspecified, this is et equal to the first listed domain in `domains`
    """

    domains: list[str]
    committee_settings: CommitteeEmailSettings
    mailing_lists: MemberMailingListAliases
    primary_domain: str = ""

    @classmethod
    def from_json(cls, filepath: str) -> Self:
        with open(filepath, "r") as fl:
            data = json.load(fl)
        return cls(
            data["domains"],
            CommitteeEmailSettings.from_dict(data["committee_aliases"]),
            {k: MemberMailingListAliasSettings.from_dict(v) for k, v in data["member_aliases"].items()},
        )

    def __post_init__(self):
        if not self.primary_domain:
            self.primary_domain = self.domains[0]


class MailingListType(Enum):
    """
    Squire's Mailcow Aliases can exist in different forms.
    - `MEMBER`: Email active members registered to the mailing list
    - `GLOBAL_COMMITTEE`: Email all committees, including non-public ones
    - `COMMITTEE`: Email all committee members, even if they're not an active member
    - `COMMITTEE_ONLY_ACTIVE`: Email committee members that are an active member
    """

    MEMBER = 0
    GLOBAL_COMMITTEE = 1
    COMMITTEE = 2
    COMMITTEE_ONLY_ACTIVE = 3


class SquireEmailManager:
    """
    Provides helper methods for managing email aliases and mailing lists.
    """

    COMMITTEE_TYPE_WHITELIST = (AssociationGroup.COMMITTEE, AssociationGroup.ORDER, AssociationGroup.WORKGROUP)

    def __init__(self):
        self.settings = EmailAliasSettings.from_json("squire/config/emailconfig.json")

    # TODO: Remove dependency on mailcow_integration. Setting up these preferences should happen in this module instead!
    @classmethod
    def mailing_list_to_id(cls, address: str) -> str:
        """Converts a mailing list address to a string compatible with django-dynamic-preferences"""
        return slugify(address)

    def get_archive_adresses_for_type(self, mailing_list_type: MailingListType, address: str = "") -> list[str]:
        """Gets a list of email addresses that are used as an archive for an alias-address"""
        match mailing_list_type:
            case MailingListType.MEMBER:
                self.settings.mailing_lists[address].archive_addresses
            case MailingListType.GLOBAL_COMMITTEE:
                self.settings.committee_settings.global_archive_addresses
            case MailingListType.COMMITTEE | MailingListType.COMMITTEE_ONLY_ACTIVE:
                self.settings.committee_settings.receive_archive_addresses
            case _:
                raise ValueError(f"Invalid mailing list type passed {mailing_list_type.name}")

    def get_active_members(self) -> QuerySet:
        """Helper method to obtain a queryset of active members. That is, those that have active membership."""
        return Member.objects.filter_active()

    def get_active_committees(self):
        """Gets a queryset containing all associationGroups that should have an alias setup"""
        return AssociationGroup.objects.filter(
            type__in=self.COMMITTEE_TYPE_WHITELIST,
            contact_email__isnull=False,
        )

    # TODO: Remove duplicates like these in SquireMailcowManager
    def get_subscribed_members(
        self, active_members: QuerySet[Member], alias_address: str, default: bool = True
    ) -> QuerySet[Member]:
        """Gets a Queryset of members subscribed to a specific member alias, based on their
        associated user's preferences. If users are opted-in by default for the given alias,
        then members without an explicit preference are included in this Queryset as well.
        If the default is opted-out, then such members are excluded.
        """
        alias_id = self.mailing_list_to_id(alias_address)

        # Find members who have a specific opt-in/opt-out status
        #   If the default is opt-out, only keep those with an explicit opt-out preference
        opts = Exists(
            UserPreferenceModel.objects.filter(
                instance_id=OuterRef("user_id"),
                section="mail",
                name=alias_id,
                raw_value=str(not default),  # dynamic preferences stores everything as a string
            )
        )

        if default:
            # If the default is opt-in, exclude users that have not
            #   explicitly opted-out. Keep those without explicit preferences.
            opts = ~opts

        return active_members.filter(opts)
