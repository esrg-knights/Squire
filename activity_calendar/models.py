from django.conf import settings
from django.core.validators import MinValueValidator, ValidationError
from django.db import models
from django.utils import timezone

from recurrence.fields import RecurrenceField

from core.models import ExtendedUser as User, PresetImage

# Models related to the Calendar-functionality of the application.
# @since 29 JUN 2019

# Not now, but a later time (used as a default value below)
def later_rounded():
    return (timezone.now() + timezone.timedelta(hours=2)).replace(minute=0, second=0)

# Rounds the current time (used as a default value below)
def now_rounded():
    return timezone.now().replace(minute=0, second=0)

# The Activity model represents an activity in the calendar
class Activity(models.Model):
    class Meta:
        verbose_name_plural = "activities"

    # The User that created the activity
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    image = models.ForeignKey(PresetImage, blank=True, null=True, related_name="activity_image", on_delete=models.SET_NULL)
    
    # Creation and last update dates (handled automatically)
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    
    # The date at which the activity will become visible for all users
    published_date = models.DateTimeField(default=now_rounded)

    # Start and end times
    start_date = models.DateTimeField(default=now_rounded)
    end_date = models.DateTimeField(default=later_rounded)

    # Recurrence information (e.g. a weekly event)
    # This means we do not need to store (nor create!) recurring activities separately
    recurrences = RecurrenceField(blank=True, default="")

    # Maximum number of participants/slots
    # -1 denotes unlimited
    max_slots = models.IntegerField(default=-1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited slots")
    max_participants = models.IntegerField(default=-1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited participants")

    # Maximum number of slots that someone can join/create
    max_slots_join_per_participant = models.IntegerField(default=1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited slots")
    max_slots_create_per_participant = models.IntegerField(default=0, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited slots")
    
    subscriptions_required = models.BooleanField(default=True,
        help_text="People are only allowed to go to the activity if they register beforehand")

    auto_create_first_slot = models.BooleanField(default=True,
        help_text="The first slot is automatically created if someone registers for the activity.")

    # When people can start/no longer subscribe to slots
    subscriptions_open = models.DurationField(default=timezone.timedelta(days=7))
    subscriptions_close = models.DurationField(default=timezone.timedelta(hours=2))

    @property
    def image_url(self):
        if self.image is None:
            return f'{settings.STATIC_URL}images/activity_default.png'
        return self.image.image.url

    # Publishes the activity, making it visible for all users
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    # Participants already subscribed
    def get_subscribed_participants(self, recurrence_id=None):
        if not self.is_recurring:
            return Participant.objects.filter(activity_slot__parent_activity__id=self.id)

        if recurrence_id is None:
            raise TypeError("recurrence_id cannot be None if the activity is recurring")

        return Participant.objects.filter(activity_slot__parent_activity__id=self.id,
                activity_slot__recurrence_id=recurrence_id)
    
    # Number of participants already subscribed
    def get_num_subscribed_participants(self, recurrence_id=None):
        return self.get_subscribed_participants(recurrence_id).count()
    
    # Maximum number of participants
    def get_max_num_participants(self, recurrence_id=None):
        max_participants = self.max_participants

        # Users can (in theory) create at least one slot, and at least one slot can (in theory) be made
        if self.max_slots_create_per_participant != 0 and self.max_slots != 0:
            # New slots can actually be made (take into account the current limit)
            if self.max_slots < 0 or self.max_slots - self.get_num_slots(recurrence_id) > 0:
                # Only limited by this activity's participants
                return max_participants

        # Otherwise we have to deal with the limitations of the already existing slots
        cnt = 0
        for slot in self.get_slots(recurrence_id):
            # At least one slot allows for infinite participants
            if slot.max_participants < 0:
                # But may still be limited by the activity's maximum amount of participants
                return max_participants
            cnt += slot.max_participants 
        
        if max_participants < 0:
            # Infinite activity participants means we're limited by the existing slots
            return cnt
        # Otherwise it's the smallest of the two
        return min(max_participants, cnt)

    # slots already created
    def get_slots(self, recurrence_id=None):
        if not self.is_recurring:
            return ActivitySlot.objects.filter(parent_activity__id=self.id)

        if recurrence_id is None:
            raise TypeError("recurrence_id cannot be None if the activity is recurring")

        return ActivitySlot.objects.filter(parent_activity__id=self.id,
                recurrence_id=recurrence_id)
    
    # Number of slots
    def get_num_slots(self, recurrence_id=None):
        return self.get_slots(recurrence_id).count()

    # Maximum number of slots that can be created
    def get_max_num_slots(self, recurrence_id=None):
        # Users can create at least one slot
        if self.max_slots_create_per_participant != 0:
            return self.max_slots

        # Users cannot create slots; we have to work with
        # the slots that already exist
        return self.get_num_slots(self, recurrence_id)
    
    # Get the subscriptions of a user of a specific occurrence
    def get_user_subscriptions(self, user, recurrence_id=None, participants=None):
        if user.is_anonymous:
            return Participant.objects.none()
        if participants is None:
            participants = self.get_subscribed_participants(recurrence_id)
        return participants.filter(user__id=user.id)
    
    # Get the subscriptions of a user of a specific occurrence
    def get_num_user_subscriptions(self, user, recurrence_id=None, participants=None):
        return self.get_user_subscriptions(user, recurrence_id, participants).count()

    # Whether a given user is subscribed to the activity
    def is_user_subscribed(self, user, recurrence_id=None, participants=None):
        return self.get_user_subscriptions(user, recurrence_id, participants).first() is not None
    
    # Whether a user can still subscribe to the activity
    def can_user_subscribe(self, user, recurrence_id=None, participants=None, max_participants=None):
        if user.is_anonymous:
            # Must be logged in to register
            return False
        
        if not self.are_subscriptions_open(recurrence_id):
            # Must be open for registrations
            return False

        if max_participants is None:
            max_participants = self.get_max_num_participants(recurrence_id)
        
        if max_participants < 0:
            # Infinite participants are allowed
            return True

        if participants is None:
            participants = self.get_subscribed_participants(recurrence_id)

        return participants.count() < max_participants

    # Whether subscriptions are open
    def are_subscriptions_open(self, recurrence_id=None):
        if not self.is_recurring:
            recurrence_id = self.start_date

        if recurrence_id is None:
            raise TypeError("recurrence_id cannot be None if the activity is recurring")

        now = timezone.now()
        return recurrence_id - self.subscriptions_open <= now and now <= recurrence_id - self.subscriptions_close

    # String-representation of an instance of the model
    def __str__(self):
        return "{1} ({0})".format(self.id, self.title)

    # Whether the activity is recurring
    @property
    def is_recurring(self):
        return bool(self.recurrences.rdates or self.recurrences.rrules)
        
    
    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}

        # Activities must start before they can end
        if self.start_date >= self.end_date:
            errors.update({'start_date': 'Start date must be before the end date'})

        if self.subscriptions_open < self.subscriptions_close:
            errors.update({'subscriptions_open': 'Subscriptions must open before they can close'})

        if self.subscriptions_open < timezone.timedelta():
            errors.update({'subscriptions_open': 'Subscriptions must open before the activity starts'})
        
        if self.subscriptions_close < timezone.timedelta():
            errors.update({'subscriptions_close': 'Subscriptions must close before the activity starts'})

        r = self.recurrences
        if r:
            recurrence_errors = []

            # Attempting to exclude dates if no recurrence is specified
            if not r.rrules and (r.exrules or r.exdates):
                recurrence_errors.append('Cannot exclude dates if the activity is non-recurring')
                
            if recurrence_errors:
                errors.update({'recurrences': recurrence_errors})

        if errors:
            raise ValidationError(errors)
        


class ActivitySlot(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, null=True,
        help_text="If left empty, matches location with parent activity")
    start_date = models.DateTimeField(blank=True, null=True,
        help_text="If left empty, matches start date with parent activity")
    end_date = models.DateTimeField(blank=True, null=True,
        help_text="If left empty, matches end date with parent activity")
    
    # The activity that this slot belongs to
    # NB: The slot belongs to just a single _occurence_ of a (recurring) activity.
    #   Hence, we need to store both the foreign key and a date representing one if its occurences
    # TODO: Create a widget for the parent_activity_recurrence so editing is a bit more user-friendly
    parent_activity = models.ForeignKey(Activity, related_name="parent_activity", on_delete=models.CASCADE)
    recurrence_id = models.DateTimeField(blank=True, null=True,
        help_text="If the activity is recurring, set this to the date/time of one of its occurences. Leave this field empty if the parent activity is non-recurring.",
        verbose_name="parent activity date/time")

    participants = models.ManyToManyField(User, blank=True, through="Participant", related_name="participant_info")
    max_participants = models.IntegerField(default=-1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited participants")

    image = models.ForeignKey(PresetImage, blank=True, null=True, related_name="slot_image", on_delete=models.SET_NULL,
        help_text="If left empty, matches the image of the parent activity.")

    def __str__(self):
        return f"{self.id}"

    @property
    def image_url(self):
        if self.image is None:
            return self.parent_activity.image_url
        return self.image.image.url

    @property
    def subscriptions_open_date(self):
        return self.recurrence_id - self.parent_activity.subscriptions_open
    
    @property
    def subscriptions_open_date(self):
        return self.recurrence_id - self.parent_activity.subscriptions_open

    # Participants already subscribed
    def get_subscribed_participants(self):
        return self.participants
    
    # Number of participants already subscribed
    def get_num_subscribed_participants(self):
        return get_subscribed_participants().count()

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}

        # Activities must start before they can end
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors.update({'start_date': 'Start date must be before the end date'})

        if self.recurrence_id is None:
            # Must set a recurrence-ID if the parent activity is recurring
            if self.parent_activity.is_recurring:
                errors.update({'recurrence_id': 'Must set a date/time as the parent activity is recurring'})
        else:
            # Must not set a recurrence-ID if the parent activity not is recurring
            if not self.parent_activity.is_recurring:
                errors.update({'recurrence_id': 'Must NOT set a date/time as the parent activity is NOT recurring'})
            elif self.recurrence_id not in self.parent_activity.recurrences.between(self.recurrence_id, self.recurrence_id, dtstart=self.parent_activity.start_date, inc=True):
                errors.update({'recurrence_id': 'Parent activity has no occurence at the given date/time'})

        # Start/end times must be within start/end times of parent activity
        if self.start_date and self.start_date < self.parent_activity.start_date:
             errors.update({'start_date': 'Start date cannot be before the start date of the parent activity'})
        if self.start_date and self.end_date > self.parent_activity.end_date:
             errors.update({'end_date': 'End date cannot be after the end date of the parent activity'})

        if errors:
            raise ValidationError(errors)

class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_slot = models.ForeignKey(ActivitySlot, on_delete=models.CASCADE)
    showed_up = models.BooleanField(null=True, default=None, help_text="Whether the participant actually showed up")
