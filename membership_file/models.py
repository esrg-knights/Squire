from django.conf import settings
from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import RegexValidator, MinValueValidator

# Models related to the Membership File-functionality of the application.
# @author E.M.A. Arts
# @since 06 JUL 2019


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
    first_name = models.CharField(max_length=63)
    tussenvoegsel = models.CharField(max_length=15, blank=True, null=True)
    last_name = models.CharField(max_length=63)
    
    # The card numbers of the member
    # NB: These card numbers must be unique
    # NB: These numbers may start with 0, which is why they are not IntegerFields
    card_number_regex = RegexValidator(regex=r'^[0-9]*$', message="Card numbers must only consist of numbers.")
    tue_card_number = models.CharField(validators=[card_number_regex], max_length=15, blank=True, null=True, unique=True)
    external_card_number = models.CharField(validators=[card_number_regex], max_length=15, blank=True, null=True, unique=True)

    # The date of birth of the member
    date_of_birth = models.DateField(default=datetime.date(1970,1,1))

    # Email address of the member
    email = models.EmailField(unique=True)

    # Telephone number of the member
    phone_regex = RegexValidator(regex=r'^\+[0-9]{8,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 14 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=16, blank=True, null=True, unique=True)

    # Address of the member
    street = models.CharField(max_length=63)
    house_number = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    house_number_addition = models.CharField(max_length=15, blank=True, null=True)
    city_of_residence = models.CharField(max_length=63)
    #NB: This is the Dutch variant of postal codes, it will differ between countries!
    postal_code_regex = RegexValidator(regex=r'^[0-9]{4} [A-Z]{2}$', message="Postal Code (Dutch variant) must be entered in the format: '1234 AB'.")
    postal_code = models.CharField(validators=[postal_code_regex], max_length=7)

    # The date at which the member became a member (automatically handled)
    member_since = models.DateField(auto_now_add=True)

    # The date and time at which this member's information was last updated
    # Handled automatically by Django
    last_updated_date = models.DateTimeField(auto_now=True)

    # String-representation of an instance of a Member
    def __str__(self):
        return "{1} {2} {3} ({0})".format(self.id, self.first_name, self.tussenvoegsel, self.last_name)

    # Gets the name of the member
    def getFullName(self):
        if hasattr(self, 'tussenvoegsel'):
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
        on_delete = models.CASCADE,
        related_name = "updated_member"
    )

    # The name of the field that was updated
    field = models.CharField(max_length=63)

    # The old value of the field
    old_value = models.CharField(max_length=63)

    # The new value of the field
    new_value = models.CharField(max_length=63)

    # String-representation of an instance of a MemberLog
    def __str__(self):
        return "{1} updated {2}'s {3}-information ({0})".format(self.id, self.user, self.member, self.field)
    