from django.apps import apps
from django.db.models.signals import post_save, post_delete

from mailcow_integration.squire_mailcow import SquireMailcowManager, get_mailcow_manager

__all__ = [
    'post_save_member_add_to_alias', 'post_delete_member'
]

def register_signals() -> None:
    """ Registers signals that activate when member info changes """
    post_save.connect(post_save_member_add_to_alias, sender='membership_file.Member', dispatch_uid="alias_member_save")
    post_delete.connect(post_delete_member_remove_from_alias, sender='membership_file.Member', dispatch_uid="alias_member_delete")

def post_save_member_add_to_alias(sender, instance, created: bool, raw: bool, **kwargs) -> None:
    """ When saving member information, adds their email to the Mailcow alias for members. """
    # Do not create logs if the database is not yet in a consistent state (happens with fixtures)
    if raw:
        return

    # No need to do anything if the member's email hasn't changed
    #   Note: instance.old_values is set in a `pre_save` signal registered in `membership_file.auto_model_update`
    if instance.old_values.get('email') == instance.email:
        print("Member email hasn't changed")
        return

    # Update member/committee mail aliases
    mailcow_client: SquireMailcowManager = get_mailcow_manager()
    mailcow_client.update_member_aliases()
    # TODO: committees

def post_delete_member_remove_from_alias(sender, instance, **kwargs):
    """ When saving member information, removes their email to the Mailcow alias for members.
    """
    # TODO
    _mailcow_client: SquireMailcowManager = get_mailcow_manager()
    print(_mailcow_client)
