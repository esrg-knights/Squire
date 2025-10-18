from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Set

from gworkspace_integration.api.base import WorkspaceAPIResponse


@dataclass
class WorkspaceGroup(WorkspaceAPIResponse):
    """
    A group in Google Workspace. Note that this is an incomplete specification.

    See: https://developers.google.com/workspace/admin/directory/reference/rest/v1/groups#Group
    """

    id: str | None = None
    email: str = ""
    name: str = ""
    description: str = ""
    adminCreated: bool = True
    directMembersCount: int = 0
    kind: str = "admin#directory#group"
    etag: str = ""
    aliases: list[str] = field(default_factory=list)
    nonEditableAliases: list[str] = field(default_factory=list)

    _cleanable_bools = ("adminCreated",)
    _cleanable_ints = ("directMembersCount",)
    _cleanable_strings = ("id", "email", "name", "description", "kind", "etag")

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] | None = None):
        aliases = json.get("aliases", [])
        if isinstance(aliases, list):
            aliases = [str(alias) for alias in aliases]
        else:  # pragma: no cover
            cls._issue_warning("aliases", aliases, "list")
            aliases = []

        nonEditableAliases = json.get("aliases", [])
        if isinstance(nonEditableAliases, list):
            nonEditableAliases = [str(alias) for alias in nonEditableAliases]
        else:  # pragma: no cover
            cls._issue_warning("nonEditableAliases", nonEditableAliases, "list")
            nonEditableAliases = []

        new_json = {"aliases": aliases, "nonEditableAliases": nonEditableAliases}

        extra_keys = extra_keys or set()
        new_json.update(**super().clean(json, extra_keys=new_json.keys() | extra_keys))
        return new_json


class WorkspaceGroupJoinPermissions(Enum):
    """Permission to join group"""

    ANYONE_CAN_JOIN = "ANYONE_CAN_JOIN"
    ALL_IN_DOMAIN_CAN_JOIN = "ALL_IN_DOMAIN_CAN_JOIN"
    INVITED_CAN_JOIN = "INVITED_CAN_JOIN"
    CAN_REQUEST_TO_JOIN = "CAN_REQUEST_TO_JOIN"


class WorkspaceGroupViewPermissions(Enum):
    """Generic view permissions"""

    ALL_OWNERS_CAN_VIEW = "ALL_OWNERS_CAN_VIEW"  # undocumented in API specs
    ALL_MANAGERS_CAN_VIEW = "ALL_MANAGERS_CAN_VIEW"
    ALL_MEMBERS_CAN_VIEW = "ALL_MEMBERS_CAN_VIEW"
    ALL_IN_DOMAIN_CAN_VIEW = "ALL_IN_DOMAIN_CAN_VIEW"


class WorkspaceGroupViewPermissionsExt(WorkspaceGroupViewPermissions):
    """Extended view permissions"""

    ANYONE_CAN_VIEW = "ANYONE_CAN_VIEW"


class WorkspaceGroupPostPermissions(Enum):
    """Generic post permissions"""

    NONE_CAN_POST = "ALL_OWNERS_CAN_VIEW"
    ALL_OWNERS_CAN_POST = "ALL_OWNERS_CAN_POST"
    ALL_MANAGERS_CAN_POST = "ALL_MANAGERS_CAN_POST"
    ALL_MEMBERS_CAN_POST = "ALL_MEMBERS_CAN_POST"
    ALL_IN_DOMAIN_CAN_POST = "ALL_IN_DOMAIN_CAN_POST"
    ANYONE_CAN_POST = "ANYONE_CAN_POST"  # Recommended to set messageModerationlevel to MODERATE_NON_MEMBERS


class WorkspaceGroupMessageModerationPermissions(Enum):
    """Moderation permissions"""

    MODERATE_ALL_MESSAGES = "MODERATE_ALL_MESSAGES"
    MODERATE_NON_MEMBERS = "MODERATE_NON_MEMBERS"
    MODERATE_NEW_MEMBERS = "MODERATE_NEW_MEMBERS"
    MODERATE_NONE = "MODERATE_NONE"


class WorkspaceGroupModerationLevel(Enum):
    """Specifies moderation levels for messages detected as spam"""

    ALLOW = "ALLOW"
    MODERATE = "MODERATE"
    SILENTLY_MODERATE = "SILENTLY_MODERATE"
    REJECT = "REJECT"


class WorkspaceGroupReplyTo(Enum):
    """Who receives the default reply"""

    REPLY_TO_CUSTOM = "REPLY_TO_CUSTOM"
    REPLY_TO_SENDER = "REPLY_TO_SENDER"
    REPLY_TO_LIST = "REPLY_TO_LIST"
    REPLY_TO_OWNER = "REPLY_TO_OWNER"
    REPLY_TO_IGNORE = "REPLY_TO_IGNORE"
    REPLY_TO_MANAGERS = "REPLY_TO_MANAGERS"


class WorkspaceGroupLeavePermissions(Enum):
    """Leave permissions"""

    ALL_MANAGERS_CAN_LEAVE = "ALL_MANAGERS_CAN_LEAVE"
    ALL_MEMBERS_CAN_LEAVE = "ALL_MEMBERS_CAN_LEAVE"
    NONE_CAN_LEAVE = "NONE_CAN_LEAVE"


class WorkspaceGroupContactPermissions(Enum):
    """Contact permissions"""

    ALL_MANAGERS_CAN_CONTACT = "ALL_MANAGERS_CAN_CONTACT"
    ALL_MEMBERS_CAN_CONTACT = "ALL_MEMBERS_CAN_CONTACT"
    ALL_IN_DOMAIN_CAN_CONTACT = "ALL_IN_DOMAIN_CAN_CONTACT"
    ANYONE_CAN_CONTACT = "ANYONE_CAN_CONTACT"


class WorkspaceGroupModerationPermissions(Enum):
    """Moderation permissions"""

    ALL_MEMBERS = "ALL_MEMBERS"
    OWNERS_AND_MANAGERS = "OWNERS_AND_MANAGERS"
    OWNERS_ONLY = "OWNERS_ONLY"
    NONE = "ANYONE_NONECAN_CONTACT"


class WorkspaceGroupDiscoverPermissions(Enum):
    """Discovery settings"""

    ALL_MEMBERS_CAN_DISCOVER = "ALL_MEMBERS_CAN_DISCOVER"
    ALL_IN_DOMAIN_CAN_DISCOVER = "ALL_IN_DOMAIN_CAN_DISCOVER"
    ANYONE_CAN_DISCOVER = "ANYONE_CAN_DISCOVER"


class WorkspaceGroupDefaultSender(Enum):
    """Default sender for members who can post messages as the group"""

    DEFAULT_SELF = "DEFAULT_SELF"
    GROUP = "GROUP"


# NB: Locked groups (https://support.google.com/a/answer/15634160?hl=en) are unavailable for "Google Workspace for Nonprofits" plans
@dataclass
class WorkspaceGroupSettings(WorkspaceAPIResponse):
    """
    Group settings in Google Workspace. Note that this is an incomplete specification.

    See: https://developers.google.com/workspace/admin/groups-settings/v1/reference/groups#resource
    """

    email: str
    name: str = ""
    description: str = ""
    whoCanJoin: WorkspaceGroupJoinPermissions = WorkspaceGroupJoinPermissions.INVITED_CAN_JOIN
    whoCanViewMembership: WorkspaceGroupViewPermissions = (
        WorkspaceGroupViewPermissions.ALL_OWNERS_CAN_VIEW
    )  # Permissions to view membership
    whoCanViewGroup: WorkspaceGroupViewPermissionsExt = (
        WorkspaceGroupViewPermissionsExt.ALL_OWNERS_CAN_VIEW
    )  # Permissions to view group messages
    allowExternalMembers: bool = True
    whoCanPostMessage: WorkspaceGroupPostPermissions = WorkspaceGroupPostPermissions.ALL_OWNERS_CAN_POST
    allowWebPosting: bool = True
    primaryLanguage: str = "en-GB"
    isArchived: bool = True  # Allows the Group contents to be archived
    archiveOnly: bool = True  # when archivedOnly, the group is inactive and new messages are rejected
    messageModerationLevel: WorkspaceGroupMessageModerationPermissions = (
        WorkspaceGroupMessageModerationPermissions.MODERATE_NONE
    )
    spamModerationLevel: WorkspaceGroupModerationLevel = WorkspaceGroupModerationLevel.MODERATE
    replyTo: WorkspaceGroupReplyTo = WorkspaceGroupReplyTo.REPLY_TO_IGNORE
    customReplyTo: str = ""
    includeCustomFooter: bool = False
    customFooterText: str = ""
    sendMessageDenyNotification: bool = True
    defaultMessageDenyNotificationText: str = ""
    membersCanPostAsTheGroup: bool = True
    includeInGlobalAddressList: bool = False
    whoCanLeaveGroup: WorkspaceGroupLeavePermissions = WorkspaceGroupLeavePermissions.NONE_CAN_LEAVE
    whoCanContactOwner: WorkspaceGroupContactPermissions = WorkspaceGroupContactPermissions.ALL_MEMBERS_CAN_CONTACT
    favoriteRepliesOnTop: bool = True
    whoCanModerateMembers: WorkspaceGroupModerationPermissions = (
        WorkspaceGroupModerationPermissions.OWNERS_AND_MANAGERS
    )
    whoCanModerateContent: WorkspaceGroupModerationPermissions = WorkspaceGroupModerationPermissions.ALL_MEMBERS
    whoCanAssistContent: WorkspaceGroupModerationPermissions = WorkspaceGroupModerationPermissions.ALL_MEMBERS
    enableCollaborativeInbox: bool = False
    whoCanDiscoverGroup: WorkspaceGroupDiscoverPermissions = (
        WorkspaceGroupDiscoverPermissions.ALL_IN_DOMAIN_CAN_DISCOVER
    )
    defaultSender: WorkspaceGroupDefaultSender = WorkspaceGroupDefaultSender.GROUP
