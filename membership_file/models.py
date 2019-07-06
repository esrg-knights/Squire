from django.conf import settings
from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import RegexValidator

# Models related to the Membership File-functionality of the application.
# @author E.M.A. Arts
# @since 06 JUL 2019


# The Member model represents a Member in the membership file
class Member(models.Model):
    # The User that is linked to this member
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        blank = True,
        null = True,
        )
    
    # The name of the member
    first_name = models.CharField(max_length=64)
    tussenvoegsel = models.CharField(max_length=16, blank=True)
    last_name = models.CharField(max_length=64)
    
    # The card numbers of the member
    tue_card_number = models.CharField(max_length=8, blank=True)
    external_card_number = models.CharField(max_length=16, blank=True) #TODO: Check the external card number length

    # The date of birth of the member
    date_of_birth = models.DateField(default=datetime.date(1970,1,1))

    # Email address of the member
    email = models.EmailField()

    # Telephone number of the member
    phone_regex = RegexValidator(regex=r'^\+\d{8,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 14 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=16, blank=True)

    # The date at which the member became a member (automatically handled)
    member_since = models.DateField(auto_now_add=True)

    # The date and time at which this member's information was last updated
    last_updated_date = models.DateTimeField(auto_now=True)

    # String-representation of an instance of the model
    def __str__(self):
        return "{1} {2} {3} ({0})".format(self.id, self.first_name, self.tussenvoegsel, self.last_name)