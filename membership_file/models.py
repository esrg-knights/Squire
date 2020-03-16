from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from datetime import date

import datetime
import re

from core.models import ExtendedUser as User

##################################################################################
# Models related to the Membership File-functionality of the application.
# @since 06 JUL 2019
##################################################################################

# Display method for a user that may also be a member
def get_member_display_name(user):
    member = MemberUser(user.id).get_member()
    if member is not None:
        return member.get_full_name()
    return user.get_simple_display_name()

# Users should be displayed by their names according to the membership file (if they're a member)
User.set_display_name_method(get_member_display_name)

# Provides additional methods on the ExtendedUser model
class MemberUser(User):
    class Meta:
        proxy = True

    # Returns the associated member to a given user
    def get_member(self):
        return Member.objects.filter(user__id=self.id).first()

    # Checks whether a given user is a member
    def is_member(self):
        return self.get_member() is not None


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

    ##################################
    # NAME
    ##################################
    initials_regex = RegexValidator(regex=r'^([A-Z]\.)+$', message="Initials must be capital letters only, and must be separated by dots. E.g. A.B.")
    initials = models.CharField(validators=[initials_regex], max_length=15, null=True, help_text="Initials as known by your Educational Institution.")
    first_name = models.CharField(max_length=255)
    tussenvoegsel = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255)
    
    ##################################
    # STUDENT INFORMATION
    ##################################
    student_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    educational_institution = models.CharField(max_length=255)

    ##################################
    # CARD NUMBERS
    # NB: These card numbers must be unique
    # NB: These numbers may start with 0, which is why they are not IntegerFields
    ##################################
    tue_card_number_regex = RegexValidator(regex=r'^[0-9]{7}$', message="TUe card numbers must only consist of exactly 7 numbers. E.g. 1234567")
    tue_card_number = models.CharField(validators=[tue_card_number_regex], max_length=15, blank=True, null=True, unique=True, verbose_name="TUe card number")
    
    external_card_digits_regex = RegexValidator(regex=r'^[0-9]{3}$', message="External card digits must consist of exactly 3 digits. E.g. 012")
    
    # External card uses the same number formatting as Tue cards, but its number does not necessarily need to be unique
    external_card_number = models.CharField(validators=[tue_card_number_regex], max_length=15, blank=True, null=True)
    # 3-digit code at the bottom of a card
    external_card_digits = models.CharField(validators=[external_card_digits_regex], max_length=3, blank=True, null=True, verbose_name="digits")
    # The cluster contains additional information of an external card
    external_card_cluster = models.CharField(max_length=255, blank=True, null=True, verbose_name="cluster") 

    # External card number and digit-pairs are a unique combination
    unique_together = [['external_card_number', 'external_card_digits']]

    ##################################
    # CONTACT INFORMATION
    ##################################
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
    state = models.CharField(max_length=255, blank=True, null=True, verbose_name="state/province")
    country = models.CharField(max_length=255)

    ##################################
    # OTHER INFORMATION
    ##################################
    # The date of birth of the member
    date_of_birth = models.DateField(default=datetime.date(1970,1,1))

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
    
    ##################################
    # STRING REPRESENTATION METHODS
    ##################################
    # String-representation of an instance of a Member
    def __str__(self):
        return self.get_full_name() + " ({0})".format(self.id)

    # Gets the name of the member
    def get_full_name(self):
        if self.tussenvoegsel is not None:
            return "{0} {1} {2}".format(self.first_name, self.tussenvoegsel, self.last_name)
        return "{0} {1}".format(self.first_name, self.last_name)

    # Gets the name of the person that last updated this user
    def display_last_updated_name(self):
        if self.last_updated_by is None:
            return None
        updater = Member.objects.filter(user__id=self.last_updated_by.id).first()
        if updater is None:
            return User.objects.filter(id=self.last_updated_by.id).first().username
        if updater.id == self.id:
            return 'You'
        return updater.get_full_name()
    
    # Displays the external card number of the member
    def display_external_card_number(self):
        if self.external_card_number is None:
            return None
        if self.external_card_cluster is None:
            # Not all external cards have a cluster
            return "{0}-{1}".format(self.external_card_number, self.external_card_digits)
        if self.external_card_digits is None:
            # Not all external cards have a 3-digit code (E.g. parking cards)
            return "{0} ({1})".format(self.external_card_number, self.external_card_cluster)
        return "{0}-{1} ({2})".format(self.external_card_number, self.external_card_digits, self.external_card_cluster)

    # Displays a user's address
    def display_address(self):
        house_number = str(self.house_number)
        if self.house_number_addition is not None:
            # If the house number starts with a number, add a dash
            if not self.house_number_addition[:1].isalpha():
                house_number += '-'
            house_number += self.house_number_addition

        return "{0} {1}, {2}, {3}{4}".format(self.street, house_number, self.city, 
            "" if self.state is None else f"{self.state}, ", self.country)

##################################################################################

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
