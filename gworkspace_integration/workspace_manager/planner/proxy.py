from dataclasses import dataclass, field

from collections.abc import Iterable
from typing import Generic, TypeVar
from typing_extensions import Self

from committees.email import MemberMailingListAlias, SquireEmailManager
from committees.models import AssociationGroup
from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import WorkspaceGroup, WorkspaceGroupMemberType
from gworkspace_integration.api.formats.users import WorkspaceUser
from membership_file.models import Member


@dataclass
class WorkspaceGroupProxy:
    """A proxy class for data displaying a mailing list configuration"""

    uuid: str
    name: str
    type: str
    email: str
    pk: int | None = None
    description: str = ""
    is_public: bool = False
    can_opt_out: bool = True
    default_opt_in: bool = False
    members: Iterable["WorkspaceGroupMemberProxy"] = field(default_factory=list)

    @classmethod
    def from_committee(cls, committee: AssociationGroup) -> Self:
        """Construct from a Committee"""
        return cls(
            f"committee-{committee.pk}",
            pk=committee.pk,
            name=committee.name,
            type=committee.get_type_display(),
            description=committee.short_description,
            email=committee.contact_email,
            is_public=True,
            can_opt_out=False,
            default_opt_in=True,
            members=[WorkspaceGroupMemberSqMember.from_proxy(m) for m in committee.members.all()],
        )

    @classmethod
    def from_member_mailing_list(cls, mailing_list: MemberMailingListAlias) -> Self:
        """Construct from a member alias"""
        email, settings = mailing_list
        return cls(
            f"memberalias-{SquireEmailManager.mailing_list_to_id(email)}",
            pk=None,
            name=settings.title,
            type="Member Alias",
            description=settings.description,
            email=email,
            is_public=not settings.internal,
            can_opt_out=settings.allow_opt_out,
            default_opt_in=settings.default_opt,
            members=[
                WorkspaceGroupMemberSqMember.from_proxy(m)
                for m in SquireEmailManager.get_subscribed_members(mailing_list)
            ],
        )

    @classmethod
    def from_committee_mailing_list(cls, email: str) -> Self:
        """Construct from a committee alias"""
        return cls(
            f"committeealias-{SquireEmailManager.mailing_list_to_id(email)}",
            pk=None,
            name=email.capitalize().split("@")[0],
            type="Committee Alias",
            description="All committees in Squire.",
            email=email,
            is_public=False,
            can_opt_out=False,
            default_opt_in=True,
            members=[WorkspaceGroupMemberCommittee.from_proxy(m) for m in SquireEmailManager.get_active_committees()],
        )


T = TypeVar("T")


@dataclass
class WorkspaceGroupMemberProxy(Generic[T]):
    """A proxy class as a Workspace Group member"""

    source_obj: T
    name: str
    email: str
    type: WorkspaceGroupMemberType = WorkspaceGroupMemberType.USER

    @classmethod
    def from_proxy(cls, proxy: T) -> Self:
        raise NotImplementedError("Subclasses should override this")

    def is_valid(self, settings: GoogleWorkspaceSettings) -> bool:
        """Is this proxy valid?"""
        return True

    def is_manual(self, settings: GoogleWorkspaceSettings) -> bool:
        """Was this member added manuallY?"""
        return False


class WorkspaceGroupMemberSqMember(WorkspaceGroupMemberProxy[Member]):
    """Squire Member as a Workspace Group member"""

    @classmethod
    def from_proxy(cls, proxy: Member):
        return cls(proxy, proxy.get_full_name(allow_spoof=False), proxy.email)

    def is_valid(self, settings: GoogleWorkspaceSettings) -> bool:
        if self.email == settings.directory_admin_username:
            return True

        return not self.email.endswith(settings.primary_domain) and not any(
            self.email.endswith(domain) for domain in settings.domains
        )


class WorkspaceGroupMemberCommittee(WorkspaceGroupMemberProxy[AssociationGroup]):
    """Committee as a Workspace Group Member"""

    @classmethod
    def from_proxy(cls, proxy: AssociationGroup) -> Self:
        return cls(proxy, proxy.name, proxy.contact_email, WorkspaceGroupMemberType.GROUP)

    def is_valid(self, settings: GoogleWorkspaceSettings) -> bool:
        # Only domain email addresses are valid
        return self.email.endswith(settings.primary_domain) or any(
            self.email.endswith(domain) for domain in settings.domains
        )


class WorkspaceGroupMemberWGroup(WorkspaceGroupMemberProxy[WorkspaceGroup]):
    """Workspace Group as a Workspace Group Member"""

    @classmethod
    def from_proxy(cls, proxy: WorkspaceGroup):
        return cls(proxy, proxy.name, proxy.email, WorkspaceGroupMemberType.GROUP)


class WorkspaceGroupMemberWUser(WorkspaceGroupMemberProxy[WorkspaceUser]):
    """Workspace User as a Workspace Group Member"""

    @classmethod
    def from_proxy(cls, proxy: WorkspaceUser):
        return cls(proxy, proxy.name.fullName, proxy.primaryEmail)

    def is_manual(self, settings) -> bool:
        return self.source_obj.orgUnitPath != settings.members_ou and self.email != settings.directory_admin_username
