from django.apps import apps
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, ModelSignal
from typing import Callable, Tuple

from mailcow_integration.squire_mailcow import SquireMailcowManager, get_mailcow_manager

__all__ = [
    'post_save_member_add_to_alias', 'post_delete_member'
]

def register_signals() -> None:
    """ Registers signals that handle Mailcow aliases """
    for (signal_method, call_method, sender, dispatch_uid) in ALIAS_SIGNALS:
        signal_method.connect(call_method, sender=sender, dispatch_uid=dispatch_uid)
    # post_save.connect(post_save_member_add_to_alias, sender='membership_file.Member', dispatch_uid="alias_member_save")
    # post_delete.connect(post_delete_member_remove_from_alias, sender='membership_file.Member', dispatch_uid="alias_member_delete")

def deregister_signals() -> None:
    """ Deregisters signals that handle Mailcow aliases """
    for (signal_method, call_method, sender, dispatch_uid) in ALIAS_SIGNALS:
        signal_method.disconnect(call_method, sender=sender, dispatch_uid=dispatch_uid)


#########################################
# MEMBERS
#########################################
def pre_save_member(sender, instance, raw, **kwargs):
    """ Temporarily stores some data when a member is updated. This data
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

def post_save_member(sender, instance, created: bool, raw: bool, **kwargs) -> None:
    """ Update member and committee aliases when a member is updated/created. """
    # Do not create logs if the database is not yet in a consistent state (happens with fixtures)
    if raw:
        return

    # No need to do anything if the member's email hasn't changed
    if instance._mailcow_old_data.get('email') == instance.email:
        return

    # Member is not active
    if not instance.is_active:
        return

    # Update member/committee mail aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    # Update member aliases
    mailcow_client.update_member_aliases()

    # Update committee aliases (only for committees the member is part of)
    comm_model = apps.get_model("committees", "AssociationGroup")
    addresses = comm_model.objects.filter(members__email=instance.email).values_list("contact_email", flat=True)
    mailcow_client.update_committee_aliases(addresses)

def pre_delete_member(sender, instance, **kwargs):
    """ Temporarily stores some data when a member is removed """
    # Committee membership data will no longer be present when post_delete activates.
    comm_model = apps.get_model("committees", "AssociationGroup")
    addresses = comm_model.objects.filter(members__email=instance.email).values_list("contact_email", flat=True)

    instance._mailcow_old_data = {
        "committee_addresses": addresses,
    }

def post_delete_member(sender, instance, **kwargs):
    """ Update member and committee aliases when a member is deleted """
    # Member is not active
    if not instance.is_active:
        return

    # Update member/committee mail aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    # Update member aliases
    mailcow_client.update_member_aliases()

    # Update committee aliases (only for committees the member is part of)
    mailcow_client.update_committee_aliases(instance._mailcow_old_data["committee_addresses"])


#########################################
# COMMITTEES
#########################################
def pre_save_committee(sender, instance, raw, **kwargs):
    """ Temporarily stores some data when a committee is updated. This data
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

def post_save_committee(sender, instance, created: bool, raw: bool, **kwargs):
    """ Update (global) committee aliases when a committee is updated/created.
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
        elif instance._mailcow_old_data["type"] in [comm_model.COMMITTEE, comm_model.GUILD, comm_model.WORKGROUP]:
            # Committee was eligible for an alias
            if instance.type not in [comm_model.COMMITTEE, comm_model.GUILD, comm_model.WORKGROUP]:
                # Committee is no longer eligible for an alias (e.g. it is a board)
                should_remove = True

    if should_remove:
        # Delete alias
        mailcow_client.delete_committee_aliases([instance.contact_email])
        return

    if instance._mailcow_old_data["email"] == instance.contact_email:
        # Email hasn't changed; nothing to update
        return

    # Update the committee's alias, and update all global committee aliases
    mailcow_client.update_committee_aliases([instance.contact_email])
    mailcow_client.update_global_committee_aliases()

def post_delete_committee(sender, instance, **kwargs):
    """ Update (global) committee aliases when a committee is deleted. """
    comm_model = apps.get_model("committees", "AssociationGroup")
    if instance.contact_email is None or instance.type not in [comm_model.COMMITTEE, comm_model.GUILD, comm_model.WORKGROUP]:
        # Committee had no email, or was not eligible for an alias
        return
    # Delete alias
    get_mailcow_manager().delete_committee_aliases([instance.contact_email])

#########################################
# COMMITTEE MEMBERSHIP
#########################################
def pre_save_committee_membership(sender, instance, raw, **kwargs):
    """ Temporarily stores some data when committee membership is updated. This data
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

def post_save_committee_membership(sender, instance, created: bool, raw: bool, **kwargs):
    """ Update member and committee aliases when a committee is updated/created.
        The aliases are only updated here, as at this point the data was successfully
        updated in the database.
    """
    if raw:
        return

    mailcow_client: SquireMailcowManager = get_mailcow_manager()

    if created:
        if instance.member.is_active:
            comm_model = apps.get_model("committees", "AssociationGroup")
            addresses = comm_model.objects.filter(members__email=instance.member.email).values_list("contact_email", flat=True)
            mailcow_client.update_member_aliases()
            mailcow_client.update_committee_aliases(addresses)
        return
    elif (instance.committee_id == instance._mailcow_old_data["committee"].id
            and instance.member_id == instance._mailcow_old_data["member"].id):
        # Attached committee and member haven't changed
        return

    # Update all member and committee aliases
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()

def post_delete_committee_membership(sender, instance, **kwargs):
    """ Update member and committee aliases when a committee is deleted. """
    if not instance.member.is_active:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()


#########################################
# ACTIVE YEARS
#########################################
def pre_save_memberyear(sender, instance, raw, **kwargs):
    """ Temporarily stores some data when a memberYear is updated. This data
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

def post_save_memberyear(sender, instance, created: bool, raw: bool, **kwargs):
    """ Update member and committee aliases when a MemberYear is updated/created.
        The aliases are only updated here, as at this point the data was successfully
        updated in the database.
    """
    if raw:
        return

    if instance.is_active == instance._mailcow_old_data["is_active"]:
        # Active years haven't changed; active members can't have changed either
        return
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    # Update all member and committee aliases
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()

def post_delete_memberyear(sender, instance, **kwargs):
    """ Update member and committee aliases when a memberYear is deleted """
    if not instance.is_active:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()

#########################################
# MEMBERSHIP
#########################################
def pre_save_membership(sender, instance, raw, **kwargs):
    """ Temporarily stores some data when a membership is updated. This data
        is then used in_post save.
    """
    if raw:
        return

    if instance.id:
        membership = apps.get_model("membership_file", "MemberShip").objects.get(id=instance.id)
        instance._mailcow_old_data = {
            "is_active": membership.year.is_active,
            "email": membership.member.email,
        }
    else:
        instance._mailcow_old_data = {
            "is_active": None,
            "email": None,
        }

def post_save_membership(sender, instance, created: bool, raw: bool, **kwargs):
    """ Update member and committee aliases when a Membership is updated/created.
        The aliases are only updated here, as at this point the data was successfully
        updated in the database.
    """
    if raw:
        return

    if created:
        if not instance.member.is_active:
            # Attached member isn't active; no need to update
            return
    elif (instance.year.is_active == instance._mailcow_old_data["is_active"]
            and instance.member.email == instance._mailcow_old_data["email"]):
        # Attached year and member haven't changed
        return

    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    # Update all member and committee aliases
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()

def post_delete_membership(sender, instance, **kwargs):
    """ Update member and committee aliases when a Membership is deleted """
    if not instance.member.is_active:
        return
    # Update all member and committee aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_member_aliases()
    mailcow_client.update_committee_aliases()

#########################################
# REGISTRATION DATA
#########################################

ALIAS_SIGNALS: Tuple[Tuple[ModelSignal, Callable, str, str], ...] = (
    # Members
    (pre_save, pre_save_member, "membership_file.Member", "alias_member_save_pre"),
    (post_save, post_save_member, "membership_file.Member", "alias_member_save_post"),
    (pre_delete, pre_delete_member, "membership_file.Member", "alias_member_delete_pre"),
    (post_delete, post_delete_member, "membership_file.Member", "alias_member_delete_post"),

    # Committees
    (pre_save, pre_save_committee, "committees.AssociationGroup", "alias_committee_save_pre"),
    (post_save, post_save_committee, "committees.AssociationGroup", "alias_committee_save_post"),
    (post_delete, post_delete_committee, "committees.AssociationGroup", "alias_committee_delete_post"),

    # AssociationGroupMembership (Member-Committee connection)

    # Active Years
    (pre_save, pre_save_memberyear, "membership_file.MemberYear", "alias_memberyear_save_pre"),
    (post_save, post_save_memberyear, "membership_file.MemberYear", "alias_memberyear_save_post"),
    (post_delete, post_delete_memberyear, "membership_file.MemberYear", "alias_memberyear_delete_post"),

    # Membership (Member-ActiveYear connection)
    (pre_save, pre_save_membership, "membership_file.Membership", "alias_membership_save_pre"),
    (post_save, post_save_membership, "membership_file.Membership", "alias_membership_save_post"),
    (post_delete, post_delete_membership, "membership_file.Membership", "alias_membership_delete_post"),
)
