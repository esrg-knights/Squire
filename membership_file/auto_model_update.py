from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .serializers import MemberSerializer
from .models import Member, MemberLog, MemberLogField

##################################################################################
# Methods that automatically create Log data when a Member gets updated
# @since 15 JUL 2019
##################################################################################

# Fires when a member gets created or updated
@receiver(pre_save, sender=Member)
def pre_save_member(sender, instance, raw, **kwargs):
    # Do not create logs if the database is not yet in a consistent state
    if raw:
        return

    # if instance is being updated, it has an id
    if instance.id:
        pPreSaveMember = Member.objects.get(pk=instance.id)

        # Pass the old values on to the post_save_member method
        # as only there can it be guaranteed that the save was successful
        instance.old_values = MemberSerializer(pPreSaveMember).data
    else:
        instance.old_values = {}

# Fires when the member update/creation has completed successfully
@receiver(post_save, sender=Member)
def post_save_member(sender, instance, created, raw, **kwargs):
    # Do not create logs if the database is not yet in a consistent state
    if raw:
        return

    old_values_that_changed = {}
    iterableMember = MemberSerializer(instance).data

    update_type = "UPDATE"

    # New Member created
    if not ('id' in instance.old_values):
        update_type = "INSERT"
        
    # Loop over all fields in the member, and store updated values
    for field in iterableMember: 
        # Skip fields that should be ignored
        if field in MemberLog.MEMBERLOG_IGNORE_FIELDS:
            continue
        # Obtain the old value
        oldValue = instance.old_values[field] if (field in instance.old_values) else None
        # If it is different, store the change
        if oldValue != iterableMember[field]:
            old_values_that_changed[field] = oldValue

    # Assert: Both dictionaries have different values for each of their keys. I.e.
    # (\forall string k; iterableMember.hasKey(k); old_values_that_changed.hasKey(k) && iterableMember[k] != old_values_that_changed[k])

    # The object was saved but no values were changed
    if not old_values_that_changed:
        return

    
    # Create a new UPDATE MemberLog
    # but only if the marked_for_deletion-value changed from T to F, or more values were changed
    if old_values_that_changed.get('marked_for_deletion', True) or len(old_values_that_changed) > 1:
        memberlog = MemberLog.objects.create(user=instance.last_updated_by, member=instance, log_type=update_type)

        # Create a new MemberLogField for each updated field
        for field in old_values_that_changed:
            # Do not create a memberLogEntry if marked_for_deletion has just changed to true or was just initialised
            if field == 'marked_for_deletion' and not old_values_that_changed[field]:
                continue

            field = MemberLogField.objects.create(member_log=memberlog, field=field, old_value=old_values_that_changed[field], new_value=iterableMember[field])
    
    # Create a special memberlog if a member got marked for deletion
    # I.e. the old value for marked_for_deletion was False
    if not old_values_that_changed.get('marked_for_deletion', True) and iterableMember.get('marked_for_deletion', False):
        # Create a new DELETE Memberlog
        MemberLog.objects.create(user=instance.last_updated_by, member=instance, log_type="DELETE")


# Fires when the member deletion has completed successfully
@receiver(post_delete, sender=Member)
def post_delete_member(sender, instance, **kwargs):
    # Manually delete all MemberLogs that are not related to a member
    # (I.e. they belonged to the just-deleted member)
    # Not enforced through a models.CASCADE as to circumvent permissions to keep the logs read only
    pMemberLogs = MemberLog.objects.filter(member=None).delete()
