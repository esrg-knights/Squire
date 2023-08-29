from functools import wraps
from typing import Callable, Tuple

from django.apps import apps
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, ModelSignal
from dynamic_preferences.registries import global_preferences_registry


from mailcow_integration.squire_mailcow import SquireMailcowManager, get_mailcow_manager

__all__ = ["register_signals", "deregister_signals", "global_preference_required_for_signal"]


def register_signals() -> None:
    """Registers signals that handle Mailcow aliases"""
    for signal_method, call_method, sender, dispatch_uid in ALIAS_SIGNALS:
        signal_method.connect(call_method, sender=sender, dispatch_uid=dispatch_uid)


def deregister_signals() -> None:
    """Deregisters signals that handle Mailcow aliases"""
    for signal_method, call_method, sender, dispatch_uid in ALIAS_SIGNALS:
        signal_method.disconnect(call_method, sender=sender, dispatch_uid=dispatch_uid)


def global_preference_required_for_signal(function=None):
    """
    Decorator that only allows signals to activate if some global preference is set
    """

    def decorator(signal_fn):
        @wraps(signal_fn)
        def _wrapped_view(*args, **kwargs):
            global_preferences = global_preferences_registry.manager()
            if global_preferences["mailcow__mailcow_signals_enabled"]:
                # Only connect to the API if the global setting allows it
                return signal_fn(*args, **kwargs)
            return

        # Wrap inside the login_required decorator (as non-logged in users can never be members)
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator


#########################################
# MEMBERS
#########################################
@global_preference_required_for_signal
def pre_save_member(sender, instance, raw, **kwargs):
    """Temporarily stores some data when a member is updated. This data
    is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        # Instance is updated: fetch old data
        member = apps.get_model("membership_file", "Member").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "email": member.email,
        }
    else:
        # New instance
        instance._mailcow_old_data = {
            "email": None,
        }


@global_preference_required_for_signal
def post_save_member(sender, instance, created: bool, raw: bool, **kwargs) -> None:
    """Update member and committee aliases when a member is updated/created."""
    # Do not create logs if the database is not yet in a consistent state (happens with fixtures)
    if raw:
        return

    # No need to do anything if the member's email hasn't changed
    if instance._mailcow_old_data.get("email") == instance.email:
        return

    # Update member/committee mail aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    # Update member aliases
    if instance.is_active:
        mailcow_client.update_member_aliases()

    # Update committee aliases (only for committees the member is part of)
    comm_model = apps.get_model("committees", "AssociationGroup")
    addresses = comm_model.objects.filter(members__email=instance.email).values_list("contact_email", flat=True)
    if addresses:
        mailcow_client.update_committee_aliases(addresses)


@global_preference_required_for_signal
def post_delete_member(sender, instance, **kwargs):
    """Update member and committee aliases when a member is deleted"""
    # Update member/committee mail aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    # Update member aliases
    if instance.is_active:
        mailcow_client.update_member_aliases()

    # NOTE: No need to update committee aliases; members cannot be deleted when they are part of one
    comm_model = apps.get_model("committees", "AssociationGroup")
    assert not comm_model.objects.filter(members__email=instance.email).values_list("contact_email", flat=True)


#########################################
# COMMITTEES
#########################################
@global_preference_required_for_signal
def pre_save_committee(sender, instance, raw, **kwargs):
    """Temporarily stores some data when a committee is updated. This data
    is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        # Instance is updated: fetch old data
        group = apps.get_model("committees", "AssociationGroup").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "email": group.contact_email,
            "type": group.type,
        }
    else:
        # New instance
        instance._mailcow_old_data = {
            "email": None,
            "type": None,
        }


@global_preference_required_for_signal
def post_save_committee(sender, instance, created: bool, raw: bool, **kwargs):
    """Update (global) committee aliases when a committee is updated/created.
    The aliases are only updated here, as at this point the data was successfully
    updated in the database.
    """
    if raw:
        return
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    comm_model = apps.get_model("committees", "AssociationGroup")

    should_remove = False

    if instance._mailcow_old_data["email"] is not None:
        # Committee used to have an alias
        if instance.contact_email is None:
            # Committee no longer has an email address
            should_remove = True
        elif instance._mailcow_old_data["type"] in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP]:
            # Committee was eligible for an alias
            if instance.type not in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP]:
                # Committee is no longer eligible for an alias (e.g. it is a board)
                should_remove = True
    elif instance.type not in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP]:
        # Committee did not have an alias previously, and shouldn't get one
        return

    if should_remove:
        # Delete alias. If a committee changes their email and is at the same time no
        #   longer eligible for an alias, we still need to pass over the old email to Mailcow.
        mailcow_client.delete_aliases([instance._mailcow_old_data["email"]])
        mailcow_client.update_global_committee_aliases()
        return

    if instance._mailcow_old_data["email"] == instance.contact_email:
        if not (
            instance.type in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP]
            and instance._mailcow_old_data["type"]
            not in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP, None]
        ):
            # Email hasn't changed, and committee remains eligible for an alias; nothing to update
            return

    # Update the committee's alias, and update all global committee aliases
    # TODO: when email changes, an orphan address is currently left behind and a new one is created
    mailcow_client.update_committee_aliases([instance.contact_email])
    mailcow_client.update_global_committee_aliases()


@global_preference_required_for_signal
def post_delete_committee(sender, instance, **kwargs):
    """Update (global) committee aliases when a committee is deleted."""
    comm_model = apps.get_model("committees", "AssociationGroup")
    if instance.contact_email is None or instance.type not in [
        comm_model.COMMITTEE,
        comm_model.ORDER,
        comm_model.WORKGROUP,
    ]:
        # Committee had no email, or was not eligible for an alias
        return
    # Delete alias
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.delete_aliases([instance.contact_email])
    mailcow_client.update_global_committee_aliases()


#########################################
# COMMITTEE MEMBERSHIP
#########################################
@global_preference_required_for_signal
def pre_save_committee_membership(sender, instance, raw, **kwargs):
    """Temporarily stores some data when committee membership is updated. This data
    is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        membership = apps.get_model("committees", "AssociationGroupMembership").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "committee": membership.group,
            "member": membership.member,
        }
    else:
        # New instance
        instance._mailcow_old_data = {
            "committee": None,
            "member": None,
        }


@global_preference_required_for_signal
def post_save_committee_membership(sender, instance, created: bool, raw: bool, **kwargs):
    """Update member and committee aliases when a committee is updated/created.
    The aliases are only updated here, as at this point the data was successfully
    updated in the database.
    """
    if raw:
        return

    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    if created:
        comm_model = apps.get_model("committees", "AssociationGroup")
        if (
            instance.member is not None
            and instance.group is not None
            and instance.group.type in [comm_model.COMMITTEE, comm_model.ORDER, comm_model.WORKGROUP]
            and instance.group.contact_email is not None
        ):
            mailcow_client.update_committee_aliases([instance.group.contact_email])
        return
    elif (
        instance.group_id == instance._mailcow_old_data["committee"].id
        and instance.member == instance._mailcow_old_data["member"]
    ):
        # Attached committee and member haven't changed
        return

    groups = [instance.group.contact_email]
    if instance.group_id != instance._mailcow_old_data["committee"].id:
        # Committee changed; need to update two aliases instead of one
        groups = [instance.group.contact_email, instance._mailcow_old_data["committee"].contact_email]
    mailcow_client.update_committee_aliases(groups)


@global_preference_required_for_signal
def post_delete_committee_membership(sender, instance, **kwargs):
    """Update member and committee aliases when a committee is deleted."""
    if instance.member is None:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_committee_aliases([instance.group.contact_email])


#########################################
# ACTIVE YEARS
#########################################
@global_preference_required_for_signal
def pre_save_memberyear(sender, instance, raw, **kwargs):
    """Temporarily stores some data when a memberYear is updated. This data
    is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        # Instance is updated: fetch old data
        year = apps.get_model("membership_file", "MemberYear").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "is_active": year.is_active,
        }
    else:
        # New instance
        instance._mailcow_old_data = {
            "is_active": False,
        }


@global_preference_required_for_signal
def post_save_memberyear(sender, instance, created: bool, raw: bool, **kwargs):
    """Update member and committee aliases when a MemberYear is updated/created.
    The aliases are only updated here, as at this point the data was successfully
    updated in the database.
    """
    if raw:
        return

    if created and (
        not instance.is_active
        or apps.get_model("membership_file", "MemberYear")
        .objects.filter(is_active=True)
        .exclude(id=instance.id)
        .exists()
    ):
        # Newly created member years cannot affect a member's active status,
        #   if there already was another active year.
        return

    if instance.is_active == instance._mailcow_old_data["is_active"]:
        # Active years haven't changed; active members can't have changed either
        return

    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    # Update all member and committee aliases
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()


@global_preference_required_for_signal
def post_delete_memberyear(sender, instance, **kwargs):
    """Update member and committee aliases when a memberYear is deleted"""
    if not instance.is_active:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()


#########################################
# MEMBERSHIP
#########################################
@global_preference_required_for_signal
def pre_save_membership(sender, instance, raw, **kwargs):
    """Temporarily stores some data when a membership is updated. This data
    is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        membership = apps.get_model("membership_file", "MemberShip").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "is_active": membership.year.is_active,
            "member": membership.member,
        }
    else:
        instance._mailcow_old_data = {
            "is_active": None,
            "member": None,
        }


@global_preference_required_for_signal
def post_save_membership(sender, instance, created: bool, raw: bool, **kwargs):
    """Update member and committee aliases when a Membership is updated/created.
    The aliases are only updated here, as at this point the data was successfully
    updated in the database.
    """
    if raw:
        return

    if created:
        if instance.member is None or not instance.year.is_active:
            # No member attached; no need to update
            return
    elif (
        instance.year.is_active == instance._mailcow_old_data["is_active"]
        and instance.member == instance._mailcow_old_data["member"]
    ):
        # Attached year and member haven't changed
        return
    elif not instance.year.is_active and not instance._mailcow_old_data["is_active"]:
        # Both years are inactive
        return

    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    if not created or instance.member.is_active:
        # Only need to update member aliases if the member was updated,
        #   or if the newly added member is active.
        mailcow_client.update_member_aliases()
    # Always update committee aliases; they can include non-active members
    mailcow_client.update_committee_aliases()


@global_preference_required_for_signal
def pre_delete_membership(sender, instance, **kwargs):
    """Temporarily stores some data when a membership is deleted"""
    if instance.member is not None:
        instance._mailcow_old_data = {
            # Member active status can change after this membership is deleted!
            "is_active": instance.member.is_active,
        }


@global_preference_required_for_signal
def post_delete_membership(sender, instance, **kwargs):
    """Update member and committee aliases when a Membership is deleted"""
    if instance.member is None or not instance.year.is_active:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    if instance._mailcow_old_data["is_active"]:
        mailcow_client.update_member_aliases()
    # Always update committee aliases; they can include non-active members
    mailcow_client.update_committee_aliases()


#########################################
# REGISTRATION DATA
#########################################

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
