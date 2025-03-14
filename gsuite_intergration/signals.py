# Strongly ~~copy-pasted~~ based on ../mailcow_integration/signals.py


from functools import wraps
from typing import Callable, Tuple


from django.apps import apps
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, ModelSignal
from dynamic_preferences.registries import global_preferences_registry


def register_signals() -> None:
    """Registers signals that handle Mailcow aliases"""
    for signal_method, call_method, sender, dispatch_uid in ALIAS_SIGNALS:
        signal_method.connect(call_method, sender=sender, dispatch_uid=dispatch_uid)


def deregister_signals() -> None:
    """Deregisters signals that handle Mailcow aliases"""
    for signal_method, call_method, sender, dispatch_uid in ALIAS_SIGNALS:
        signal_method.disconnect(call_method, sender=sender, dispatch_uid=dispatch_uid)


# Originally stolen from ../mailcow_integration/signals.py
ALIAS_SIGNALS: Tuple[Tuple[ModelSignal, Callable, str, str], ...] = (
    # Members
    (pre_save, pre_save_member, "membership_file.Member", "alias_member_save_pre"),
    (post_save, post_save_member, "membership_file.Member", "alias_member_save_post"),
    (post_delete, post_delete_member, "membership_file.Member", "alias_member_delete_post"),
    # Committees
    (pre_save, pre_save_committee, "committees.AssociationGroup", "alias_committee_save_pre"),
    (post_save, post_save_committee, "committees.AssociationGroup", "alias_committee_save_post"),
    (post_delete, post_delete_committee, "committees.AssociationGroup", "alias_committee_delete_post"),
    # AssociationGroupMembership (Member-Committee connection)
    (
        pre_save,
        pre_save_committee_membership,
        "committees.AssociationGroupMembership",
        "alias_committee_membership_save_pre",
    ),
    (
        post_save,
        post_save_committee_membership,
        "committees.AssociationGroupMembership",
        "alias_committee_membership_save_post",
    ),
    (
        post_delete,
        post_delete_committee_membership,
        "committees.AssociationGroupMembership",
        "alias_committee_membership_delete_post",
    ),
    # Active Years
    (pre_save, pre_save_memberyear, "membership_file.MemberYear", "alias_memberyear_save_pre"),
    (post_save, post_save_memberyear, "membership_file.MemberYear", "alias_memberyear_save_post"),
    (post_delete, post_delete_memberyear, "membership_file.MemberYear", "alias_memberyear_delete_post"),
    # Membership (Member-ActiveYear connection)
    (pre_save, pre_save_membership, "membership_file.Membership", "alias_membership_save_pre"),
    (post_save, post_save_membership, "membership_file.Membership", "alias_membership_save_post"),
    (pre_delete, pre_delete_membership, "membership_file.Membership", "alias_membership_delete_pre"),
    (post_delete, post_delete_membership, "membership_file.Membership", "alias_membership_delete_post"),
)
