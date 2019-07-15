# Allows methods to fire automatically if a DB-model is updated
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .serializers import MemberSerializer
from .models import Member, MemberLog, MemberLogField

##################################################################################
# Methods that automatically create Log data when a Member gets updated
# @author E.M.A. Arts
# @since 15 JUL 2019
##################################################################################

# Fires when a member gets created or updated
@receiver(pre_save, sender=Member)
def pre_save_member(sender, instance, **kwargs):

    # if instance is being updated, it has an id
    if instance.id:
        pOldMember = Member.objects.get(pk=instance.id)

        # Pass the old values on to the post_save_member method
        # as only there can it be guaranteed that the save was successful
        instance.old_values = MemberSerializer(pOldMember).data
    else:
        instance.old_values = {}

# Fires when the member update/creation has completed successfully
@receiver(post_save, sender=Member)
def post_save_member(sender, instance, created, **kwargs):

    updatedValues = {}
    iterableMember = MemberSerializer(instance).data

    for field in iterableMember: 
        oldValue = instance.old_values[field] if (field in instance.old_values) else None
        if oldValue != iterableMember[field]:
            updatedValues[field] = oldValue

    # Remove the last updated date fields
    updatedValues.pop('id', None)
    updatedValues.pop('last_updated_date', None)
    updatedValues.pop('last_updated_by', None)

    # The object was saved but no values were changed
    if not updatedValues:
        return

    # Create a new MemberLog
    memberlog = MemberLog.objects.create(user=instance.last_updated_by, member=instance)

    # Create a new MemberLogField for each updated field
    for field in updatedValues:
        field = MemberLogField.objects.create(member_log=memberlog, field=field, old_value=updatedValues[field], new_value=iterableMember[field])

