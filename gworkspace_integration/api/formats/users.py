from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Set

from gworkspace_integration.api.base import WorkspaceAPIResponse


@dataclass
class WorkspaceUserName(WorkspaceAPIResponse):
    """Name data for a Google Workspace user"""

    fullName: str = ""
    familyName: str = ""
    givenName: str = ""
    displayName: str = ""

    _cleanable_strings = ("fullName", "familyName", "givenName", "displayName")
    _optional_fields = ("displayName",)


@dataclass
class WorkspaceUserEmail(WorkspaceAPIResponse):
    """Email data for a Google Workspace user"""

    address: str = ""
    customType: str = ""
    primary: bool = False
    type: Literal["custom"] | Literal["home"] | Literal["other"] | Literal["work"] | None = None

    _cleanable_strings = ("address", "customType", "type")
    _cleanable_bools = ("primary",)
    _optional_fields = ("customType", "primary", "type")


@dataclass
class WorkspaceExternalUserId(WorkspaceAPIResponse):
    """External ID's for a Google Workspace user"""

    customType: str = ""
    type: (
        Literal["custom"]
        | Literal["customer"]
        | Literal["login_id"]
        | Literal["network"]
        | Literal["organization"]
        | None
    ) = None
    value: str = ""

    _cleanable_strings = ("customType", "type", "value")
    _optional_fields = ("customType",)


@dataclass
class WorkspaceUser(WorkspaceAPIResponse):
    """
    A user in Google Workspace. Note that this is an incomplete specification.

    See: https://developers.google.com/workspace/admin/directory/reference/rest/v1/users#User
    """

    id: str | None = None
    primaryEmail: str = ""
    password: str = ""
    hashFunction: Literal["MD5"] | Literal["SHA-1"] | Literal["crypt"] = "crypt"

    suspended: bool = False
    changePasswordAtNextLogin: bool = False
    name: WorkspaceUserName = field(default_factory=WorkspaceUserName)

    emails: list[WorkspaceUserEmail] = field(default_factory=list)
    external_ids: list[WorkspaceExternalUserId] = field(default_factory=list)

    aliases: list[str] = field(default_factory=list)

    lastLoginTime: datetime | None = None  # ISO
    suspensionReason: str = ""
    thumbnailPhotoUrl: str = ""

    creationTime: datetime | None = None  # ISO
    includeInGlobalAddressList: bool = True
    deletionTime: datetime | None = None  # ISO

    isEnrolledIn2Sv: bool = False
    isEnforcedIn2Sv: bool = False
    archived: bool = False

    orgUnitPath: str = ""
    recoveryEmail: str = ""
    recoveryPhone: str = ""

    _cleanable_bools = (
        "suspended",
        "changePasswordAtNextLogin",
        "includeInGlobalAddressList",
        "isEnrolledIn2Sv",
        "isEnforcedIn2Sv",
        "archived",
    )
    _cleanable_ints = ()
    _cleanable_strings = (
        "id",
        "primaryEmail",
        "password",
        "hashFunction",
        "suspensionReason",
        "thumbnailPhotoUrl",
        "recoveryEmail",
        "recoveryPhone",
        "orgUnitPath",
    )
    _cleanable_datetimes = ("lastLoginTime", "creationTime", "deletionTime")

    _optional_fields = (
        "primaryEmail",
        "password",
        "hashFunction",
        "deletionTime",
        "suspensionReason",
        "thumbnailPhotoUrl",
        "recoveryEmail",
        "recoveryPhone",
    )

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] | None = None):
        aliases = json.get("aliases", [])
        if isinstance(aliases, list):
            aliases = [str(alias) for alias in aliases]
        else:  # pragma: no cover
            cls._issue_warning("aliases", aliases, "list")
            aliases = []

        emails = json.get("emails", [])
        if isinstance(emails, list):
            emails = [WorkspaceUserEmail.from_json(email) or WorkspaceUserEmail() for email in emails]
        else:  # pragma: no cover
            cls._issue_warning("emails", emails, "list")
            emails = []

        ext_ids = json.get("externalIds", [])
        if isinstance(emails, list):
            ext_ids = [WorkspaceExternalUserId.from_json(ext_id) or WorkspaceExternalUserId() for ext_id in ext_ids]
        else:  # pragma: no cover
            cls._issue_warning("externalIds", ext_ids, "list")
            ext_ids = []

        new_json = {
            "name": WorkspaceUserName.from_json(json.get("name", {})) or WorkspaceUserName(),
            "aliases": aliases,
            "emails": emails,
            "external_ids": ext_ids,
        }

        extra_keys = extra_keys or set()
        new_json.update(**super().clean(json, extra_keys=new_json.keys() | extra_keys))

        # last login defaults to 1970-01-01 if never used
        last_login = new_json.get("lastLoginTime", None)
        if last_login == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc):  # pragma: no cover
            new_json["lastLoginTime"] = None

        return new_json

    def __hash__(self):
        # ID is immutable; safe to hash
        return hash(self.id)
