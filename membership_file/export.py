from import_export import resources
from import_export.fields import Field

from .models import Member, Membership


class MemberResource(resources.ModelResource):
    class Meta:
        model = Member
        fields = (
            "id",
            "first_name",
            "tussenvoegsel",
            "last_name",
            "legal_name",
            "phone_number",
            "email",
            "educational_institution",
            "student_number",
            "key_id",
            "tue_card_number",
            "full_external_card",
            "external_card_deposit",
            "accessible_rooms",
            "street",
            "house_number",
            "house_number_addition",
            "postal_code",
            "city",
            "country",
            "date_of_birth",
            "is_honorary_member",
            "member_since",
            "is_deregistered",
            "email_deregistered_member",
            "notes_single_line",
        )
        export_order = fields

    full_external_card = Field()
    accessible_rooms = Field()

    # Replace newlines by spaces as MS Excel does not handle newlines in CSVs well
    notes_single_line = Field()

    # Separate the email addresses of registered and deregistered members.
    #   This is just an extra failsave to prevent accidental mailouts to people who
    #   are no longer a member, but whose email is still kept for some particular
    #   reason (e.g., they still have an external card).
    email = Field()
    email_deregistered_member = Field()

    def dehydrate_full_external_card(self, member):
        return member.display_external_card_number()

    def dehydrate_accessible_rooms(self, member):
        return " | ".join(map(str, member.accessible_rooms.all()))

    def dehydrate_notes_single_line(self, member):
        return member.notes.replace("\n", " ")

    def dehydrate_email(self, member):
        return member.email if not member.is_deregistered else None

    def dehydrate_email_deregistered_member(self, member):
        return member.email if member.is_deregistered else None


class MembersFinancialResource(resources.ModelResource):
    class Meta:
        model = Membership
        fields = (
            "member",
            "email",
            "year__name",
            "created_on",
            "has_paid",
            "payment_date",
        )
        export_order = fields

    email = Field()

    def dehydrate_email(self, membership):
        return membership.member.email

    def dehydrate_member(self, membership):
        return membership.member.get_full_name()
