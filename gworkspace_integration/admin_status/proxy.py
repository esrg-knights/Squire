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
    pk: int | None
    name: str
    type: str
    description: str
    email: str
    is_public: bool
    can_opt_out: bool
    default_opt_in: bool
    members: Iterable["MailingListMemberProxy"] = field(default_factory=list)

    @classmethod
    def from_committee(cls, committee: AssociationGroup) -> Self:
        """Construct from a Committee"""
        return cls(
            f"committee-{committee.pk}",
            committee.pk,
            committee.name,
            committee.get_type_display(),
            committee.short_description,
            committee.contact_email,
            True,
            False,
            True,
            [MailingListMemberProxy.from_member(m) for m in committee.members.all()],
        )

    @classmethod
    def from_member_mailing_list(cls, mailing_list: MemberMailingListAlias) -> Self:
        """Construct from a member alias"""
        email, settings = mailing_list
        return cls(
            f"memberalias-{SquireEmailManager.mailing_list_to_id(email)}",
            None,
            settings.title,
            "Member Alias",
            settings.description,
            email,
            not settings.internal,
            settings.allow_opt_out,
            settings.default_opt,
            [MailingListMemberProxy.from_member(m) for m in SquireEmailManager.get_subscribed_members(mailing_list)],
        )

    @classmethod
    def from_committee_mailing_list(cls, email: str) -> Self:
        """Construct from a committee alias"""
        return cls(
            f"committeealias-{SquireEmailManager.mailing_list_to_id(email)}",
            None,
            email.capitalize().split("@")[0],
            "Committee Alias",
            "All committees in Squire.",
            email,
            False,
            False,
            True,
            [MailingListMemberProxy.from_committee(m) for m in SquireEmailManager.get_active_committees()],
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
