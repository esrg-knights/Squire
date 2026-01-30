from dataclasses import dataclass, field

from collections.abc import Iterable
from typing_extensions import Self

from committees.email import MemberMailingListAlias, SquireEmailManager
from committees.models import AssociationGroup
from membership_file.models import Member


@dataclass
class MailingListProxy:
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
    members: Iterable["MailingListMemberProxy"] = field(default_factory=list)

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
            members=[MailingListMemberProxy.from_member(m) for m in committee.members.all()],
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
                MailingListMemberProxy.from_member(m) for m in SquireEmailManager.get_subscribed_members(mailing_list)
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
            members=[MailingListMemberProxy.from_committee(m) for m in SquireEmailManager.get_active_committees()],
        )


@dataclass
class MailingListMemberProxy:
    """A proxy class for mailing list members"""

    pk: int
    name: str
    email: str

    @classmethod
    def from_member(cls, member: Member) -> Self:
        """Construct from a member"""
        return cls(member.pk, member.get_full_name(allow_spoof=False), member.email)

    @classmethod
    def from_committee(cls, committee: AssociationGroup) -> Self:
        """Construct from a committee"""
        return cls(None, committee.name, committee.contact_email)
