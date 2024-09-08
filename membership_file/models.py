from decimal import Decimal
from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from datetime import date

from dynamic_preferences.registries import global_preferences_registry

from utils.spoofs import optimise_naming_scheme
from django.contrib.auth import get_user_model

User = get_user_model()

global_preferences = global_preferences_registry.manager()

##################################################################################
# Models related to the Membership File-functionality of the application.
# @since 06 JUL 2019
##################################################################################


class MemberManager(models.Manager):
    def filter_active(self):
        """Filter all 'active' members. That is, members who have a membership in
        one of the currently active years, excluding those that are specifically
        marked as 'deregistered'.
        """
        filter = self.filter(is_deregistered=False, marked_for_deletion=False)

        active_years = MemberYear.objects.filter(is_active=True).values_list("id", flat=True)
        if not active_years:
            # No active membership year set; only return registered members
            return filter

        # Active membership year set; only return members registered in these years.
        #   Honorary members are always active, regardless of active years
        return filter.filter(models.Q(memberyear__in=active_years) | models.Q(is_honorary_member=True)).distinct()


# The Member model represents a Member in the membership file
class Member(models.Model):
    class Meta:
        permissions = [
            ("can_view_membership_information_self", "[F] Can view their own membership information."),
            ("can_change_membership_information_self", "[F] Can edit their own membership information."),
            ("can_export_membership_file", "Can export the membership file."),
        ]
        ordering = ["first_name", "last_name"]

    objects = MemberManager()

    # The User that is linked to this member
    # NB: Only one user can be linked to one member at the same time!
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="member",
    )

    ##################################
    # NAME
    ##################################
    legal_name = models.CharField(
        max_length=255, help_text="Legal name as known by your Educational Institution or on your ID-card."
    )
    first_name = models.CharField(max_length=255, verbose_name="preferred name")
    tussenvoegsel = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255)

    ##################################
    # STUDENT INFORMATION
    ##################################
    EDUCATIONAL_INSTITUTION_TUE = "TU/e"
    student_number = models.CharField(max_length=15, blank=True)
    educational_institution = models.CharField(max_length=255, blank=True, default=EDUCATIONAL_INSTITUTION_TUE)

    ##################################
    # CARD NUMBERS
    # NB: These card numbers must be unique
    # NB: These numbers may start with 0, which is why they are not IntegerFields
    ##################################
    tue_card_number_regex = RegexValidator(
        regex=r"^[0-9]{8}$",
        message="TUe card numbers must only consist of exactly 8 digits. For older cards (pre 2017) that only used 7 digits, prepend a 0. E.g. 01457347",
    )
    tue_card_number = models.CharField(
        validators=[tue_card_number_regex],
        max_length=15,
        blank=True,
        null=True,
        unique=True,
        verbose_name="TUe card number",
    )

    external_card_digits_regex = RegexValidator(
        regex=r"^[0-9]{4}$", message="External card digits must consist of exactly 4 digits. E.g. 0012"
    )

    # External card uses the same number formatting as Tue cards, but its number does not necessarily need to be unique
    external_card_number = models.CharField(
        validators=[tue_card_number_regex],
        max_length=15,
        null=True,
        blank=True,
        help_text="External cards mention 'FMC', whereas Tu/e cards are currently red (since sept. 2021) or orange (before sept. 2021).",
    )
    # 4-digit code at the bottom of a card; only used for external cards
    external_card_digits = models.CharField(
        validators=[external_card_digits_regex], max_length=4, blank=True, verbose_name="digits"
    )

    # External cards require a deposit, which has changed over the years
    external_card_deposit = models.DecimalField(
        validators=[MinValueValidator(Decimal(0))],
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="deposit (€)",
        help_text="External cards require a deposit.",
    )

    # External card number and digit-pairs are a unique combination
    unique_together = [["external_card_number", "external_card_digits"]]

    key_id_regex = RegexValidator(regex=r"^[0-9]{4}$", message="Key IDs consist of exactly 4 digits. E.g. 0123")
    key_id = models.CharField(
        validators=[key_id_regex],
        max_length=7,
        blank=True,
        null=True,
        unique=True,
        help_text="A 4-digit code used to access the keysafe.",
    )

    ##################################
    # CONTACT INFORMATION
    ##################################
    # Email address of the member
    email = models.EmailField(
        max_length=255, unique=True, help_text="This email address is used by the board to contact you."
    )

    # Telephone number of the member
    phone_regex = RegexValidator(
        regex=r"^\+[0-9]{8,15}$",
        message="Phone number must be entered in the format: '+31651018209'. Up to 14 digits allowed.",
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=16,
        blank=True,
        null=True,
        unique=True,
        help_text="A phone number is required if you want access to our rooms.",
    )

    # Address of the member
    street = models.CharField(max_length=255, blank=True)
    house_number = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)
    house_number_addition = models.CharField(max_length=255, blank=True, verbose_name="addition")
    # No postal code RegEx as those have different formats in different countries (e.g. Belgium doesn't use two trailing letters)
    postal_code = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=255, blank=True, default="Eindhoven")
    country = models.CharField(max_length=255, blank=True, default="The Netherlands")

    ##################################
    # OTHER INFORMATION
    ##################################
    # The date of birth of the member
    date_of_birth = models.DateField(blank=True, null=True)

    # The date at which the member became a member (automatically handled, but is overridable)
    member_since = models.DateField(default=date.today)

    # The date and time at which this member's information was last updated
    # Handled automatically by Django, and cannot be overridden
    last_updated_date = models.DateTimeField(auto_now=True)

    # The user that last updated the member information
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="last_updated_by_user",
    )

    # Members can be marked for deletion, after which another user
    # can permanently delete the member
    marked_for_deletion = models.BooleanField(default=False)

    # Other membership statuses
    is_deregistered = models.BooleanField(
        default=False,
        help_text="Use this if you need to store (contact) information of someone who is not a member anymore.",
    )
    is_honorary_member = models.BooleanField(
        default=False, help_text="Honorary members can stay members forever and do not need to pay a membership fee."
    )

    # Any additional information that cannot be stored in other fields (e.g., preferred pronouns)
    notes = models.TextField(blank=True, help_text="Notes are invisible to members.")

    @property
    def is_active(self):
        """A member is active if it has membership in one of the active years, and if
        it is otherwise not explicitly marked as inactive (i.e., deregistered or a pending deletion).
        Behaviour is consistent with Member.objects.filter_active()
        """
        if self.is_deregistered or self.marked_for_deletion:
            return False

        # Honorary members are active regardless of active member years
        if self.is_honorary_member:
            return True

        # Do not block membership if no year is active
        if MemberYear.objects.filter(is_active=True).exists():
            return self.memberyear_set.filter(is_active=True).exists()
        return True

    ##################################
    # STRING REPRESENTATION METHODS
    ##################################
    # String-representation of an instance of a Member
    def __str__(self):
        return self.get_full_name()

    # Gets the name of the member
    def get_full_name(self, allow_spoof=True):
        """The member's full name. If `allow_spoof`, then this name can be modified for the purposes of jokes."""
        first_name = self.first_name
        if allow_spoof and global_preferences["homepage__april_2022"]:
            # This bit is from the april fools joke 2022
            first_name = optimise_naming_scheme(first_name)

        if self.tussenvoegsel:
            return "{0} {1} {2}".format(first_name, self.tussenvoegsel, self.last_name)
        return "{0} {1}".format(first_name, self.last_name)

    # Gets the name of the person that last updated this user
    def display_last_updated_name(self):
        if self.last_updated_by is None:
            return None
        if self.user == self.last_updated_by:
            return "You"
        return str(self.last_updated_by)

    # Displays the external card number of the member
    def display_external_card_number(self):
        if self.external_card_number is None:
            return None

        display_card = self.external_card_number
        if self.external_card_digits:
            # Not all external card have a 4-digit code (E.g. parking cards)
            display_card += f"-{self.external_card_digits}"

        return display_card

    # Displays a user's address
    def display_address(self):
        if not self.city:
            # Return nothing if the address is not provided
            return None

        house_number = str(self.house_number)
        if self.house_number_addition:
            # If the house number starts with a number, add a dash
            if not self.house_number_addition[:1].isalpha():
                house_number += "-"
            house_number += self.house_number_addition
        # <Street> <Number><Addition>; <Postal>, <City> (<Country>)
        return "{0} {1}; {2}, {3} ({4})".format(self.street, house_number, self.postal_code, self.city, self.country)


##################################################################################


class Room(models.Model):
    """A room that can be gained access through by a card or key."""

    name = models.CharField(max_length=63)
    room_number = models.CharField(max_length=15, blank=True)

    ACCESS_KEY = "KEY"
    ACCESS_CARD = "CARD"
    ACCESS_OTHER = "MISC"
    _ACCESS_TYPES = [
        (ACCESS_KEY, "Key"),
        (ACCESS_CARD, "TUe Card/External Card"),
        (ACCESS_OTHER, "Other"),
    ]
    access_type = models.CharField(max_length=4, choices=_ACCESS_TYPES)
    access_specification = models.CharField(max_length=15, help_text="E.g. key number", blank=True)

    notes = models.TextField(blank=True)

    # Members who have access to this room
    #   If access should be revoked temporarily (e.g., due to a suspension), this can be stored
    #   in the member's notes-field instead
    members_with_access = models.ManyToManyField(Member, blank=True, related_name="accessible_rooms")

    def __str__(self):
        access = self.get_access_type_display()
        if self.access_specification:
            access += " - " + self.access_specification
        if self.room_number:
            return f"{self.room_number} - {self.name} ({access})"
        return f"{self.name} ({access})"


##################################################################################


class MemberYear(models.Model):
    """Defines the college years periods"""

    name = models.CharField(max_length=16)
    members = models.ManyToManyField(Member, through="Membership", through_fields=["year", "member"])
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Defines membership details of a member in a certain memberyear"""

    # NULL-value allows keeping track of membership numbers over the years, even when members are deleted
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    year = models.ForeignKey(MemberYear, on_delete=models.PROTECT)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name="created_memberships")
    created_on = models.DateTimeField(auto_now_add=True)

    has_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [["member", "year"]]

    def __str__(self):
        if self.member is not None:
            return f"{self.member.get_full_name()} for {self.year}"
        return f"Deleted member for {self.year}"


# The MemberLog Model represents a log entry that is created whenever membership data is updated
class MemberLog(models.Model):
    MEMBERLOG_IGNORE_FIELDS = ["last_updated_date", "last_updated_by"]

    # The user that updated the information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_memberlogs",
        null=True,
    )

    # The member whose information was updated
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
    )

    # Possble types of updates
    LOG_TYPE_CHOICES = [
        ("INSERT", "Insert"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
    ]

    # The type of update
    log_type = models.CharField(
        max_length=255,
        choices=LOG_TYPE_CHOICES,
    )

    # The date and time at which the change was performed
    # Automatically handled by Django and cannot be overridden
    date = models.DateTimeField(auto_now_add=True)

    # String-representation of an instance of a MemberLog
    def __str__(self):
        return "[{3}] {1} updated {2}'s information ({0})".format(self.id, self.user, self.member, self.log_type)


# The MemberLogField Model represents an updated field in a MemberLog object
class MemberLogField(models.Model):
    # The user that updated the information
    member_log = models.ForeignKey(
        MemberLog,
        on_delete=models.CASCADE,
        related_name="updated_fields",
    )

    # The name of the field that was updated
    field = models.CharField(max_length=255)

    # The old value of the field
    old_value = models.TextField(null=True)

    # The new value of the field
    new_value = models.TextField(null=True)

    # String-representation of an instance of a MemberLogField
    def __str__(self):
        return "{1} was updated: <{2}> -> <{3}> ({0})".format(self.id, self.field, self.old_value, self.new_value)
