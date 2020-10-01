import logging
import os

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from import_export import resources

from .models import Member

logger = logging.getLogger('membership_file')

class MemberResource(resources.ModelResource):
    class Meta:
        model = Member
        fields = ('id', 'first_name', 'tussenvoegsel', 'last_name', 'email', 'phone_number')
        export_order = ('id', 'first_name', 'tussenvoegsel', 'last_name', 'email', 'phone_number')

    def get_queryset(self):
        return Member.objects.filter(is_deregistered=False)

class DeregisteredMemberResource(MemberResource):
    def get_queryset(self):
        return Member.objects.filter(is_deregistered=True)


@receiver(post_save, sender=Member)
def post_save_member(sender, instance, created, raw, **kwargs):
    # Do do anything if the database is not yet in a consistent state
    if raw:
        return
    export_members_to_folder()

@receiver(post_delete, sender=Member)
def post_delete_member(sender, instance, **kwargs):
    export_members_to_folder()

def export_data_to_folder(output_path, filename, csv_data):
    os.makedirs(output_path, exist_ok=True)
    output_path_file = os.path.join(output_path, filename)
    with open(output_path_file, "w", newline='') as csv_file:
        csv_file.write(csv_data)
        logger.info(f'Exported Membership Data to {output_path_file}')


# Exports the membership file to the output folder defined in the settings
def export_members_to_folder():
    output_path = settings.MEMBERSHIP_FILE_EXPORT_PATH
    if output_path is None:
        return
    
    # Export Registered Members
    csv_member_data = MemberResource().export().csv
    export_data_to_folder(output_path, "squire_membership_file.csv", csv_member_data)

    # Export Deregistered Members
    csv_member_data = DeregisteredMemberResource().export().csv
    export_data_to_folder(output_path, "squire_deregistered_members.csv", csv_member_data)

    
    
