from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import date
import datetime
from django.core.validators import RegexValidator, MinValueValidator

##################################################################################
# Models related to the Membership File-functionality of the application.
# @author E.M.A. Arts
# @since 06 JUL 2019
##################################################################################

# The Member model represents a Member in the membership file
class Member(models.Model):
    # The User that is linked to this member
    # NB: Only one user can be linked to one member at the same time!
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        blank = True,
        null = True,        
        related_name = "related_user",
        )
    
    # The name of the member
    first_name = models.CharField(max_length=255)
    tussenvoegsel = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255)
    
    # The card numbers of the member
    # NB: These card numbers must be unique
    # NB: These numbers may start with 0, which is why they are not IntegerFields
    tue_card_number_regex = RegexValidator(regex=r'^[0-9]{7}$', message="TU/e card numbers must only consist of exactly 7 numbers. E.g. 1234567")
    tue_card_number = models.CharField(validators=[tue_card_number_regex], max_length=15, blank=True, null=True, unique=True)
    
    external_card_number_regex = RegexValidator(regex=r'^[0-9]{7}\-[0-9]{3}$', message="External card numbers must only consist"
         + " of exactly 7 numbers, followed by a hyphen (-), and ended by the 'external number' which consists of exactly 3 numbers. E.g. 1234567-123")
    external_card_number = models.CharField(validators=[external_card_number_regex], max_length=15, blank=True, null=True, unique=True)
    external_card_cluster = models.CharField(max_length=255, blank=True, null=True)

    # The date of birth of the member
    date_of_birth = models.DateField(default=datetime.date(1970,1,1))

    # Email address of the member
    email = models.EmailField(max_length=255, unique=True)

    # Telephone number of the member
    phone_regex = RegexValidator(regex=r'^\+[0-9]{8,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 14 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=16, blank=True, null=True, unique=True)

    # Address of the member
    street = models.CharField(max_length=255)
    house_number = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    house_number_addition = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255)
    #NB: States/Province are not always necessary for addresses
    state = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255)
    #NB: Not all countries use postal codes! Moreover, it will differ between countries!
    postal_code_regex = RegexValidator(regex=r'^[0-9A-Za-z\-" "]*$', message="Postal Codes must only consist of alphanumerical characters, spaces, and hyphens (-).")
    postal_code = models.CharField(max_length=255, validators=[postal_code_regex])

    # The date at which the member became a member (automatically handled, but is overridable)
    member_since = models.DateField(default=date.today)

    # The date and time at which this member's information was last updated
    # Handled automatically by Django, and cannot be overridden
    last_updated_date = models.DateTimeField(auto_now=True)

    # The user that last updated the member information
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        blank = True,
        null = True,        
        related_name = "last_updated_by_user",
    )

    # Members can be marked for deletion, after which another user
    # can permanently delete the member
    marked_for_deletion = models.BooleanField(default=False)

    # String-representation of an instance of a Member
    def __str__(self):
        return self.getFullName() + " ({0})".format(self.id)

    # Gets the name of the member
    def getFullName(self):
        if self.tussenvoegsel is not None:
            return "{0} {1} {2}".format(self.first_name, self.tussenvoegsel, self.last_name)
        return "{0} {1}".format(self.first_name, self.last_name)


# The MemberLog Model represents a log entry that is created whenever membership data is updated
class MemberLog(models.Model):
    # The user that updated the information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        related_name = "user_that_updated",
        null = True,
        )
    
    # The member whose information was updated
    member = models.ForeignKey(
        Member,
        on_delete = models.SET_NULL,
        related_name = "updated_member",
        null = True,
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
        on_delete = models.CASCADE,
        related_name = "updated_in_member_log",
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
