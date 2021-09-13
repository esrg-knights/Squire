from import_export import resources
from import_export.fields import Field

from .models import Member


class MemberResource(resources.ModelResource):
    class Meta:
        model = Member
        fields = (
            'id',
            'first_name', 'tussenvoegsel', 'last_name', 'legal_name',
            'phone_number', 'email',
            'educational_institution', 'student_number',
            'key_id', 'tue_card_number', 'full_external_card', 'accessible_rooms',
            'street', 'house_number', 'house_number_addition', 'postal_code', 'city', 'country',
            'date_of_birth', 'has_paid_membership_fee', 'is_honorary_member', 'member_since',
            'is_deregistered', 'email_deregistered_member',
            'notes',
        )
        export_order = fields

    full_external_card = Field()
    accessible_rooms = Field()

    # Separate the email addresses of registered and deregistered members.
    #   This is just an extra failsave to prevent accidental mailouts to people who
    #   are no longer a member, but whose email is still kept for some particular
    #   reason (e.g., they still have an external card).
    email = Field()
    email_deregistered_member = Field()

    def dehydrate_full_external_card(self, member):
        return member.display_external_card_number()

    def dehydrate_accessible_rooms(self, member):
        return '| '.join(map(str, member.accessible_rooms.all()))

    def dehydrate_email(self, member):
        return member.email if not member.is_deregistered else None

    def dehydrate_email_deregistered_member(self, member):
        return member.email if member.is_deregistered else None

