import copy
import datetime

from django.conf import settings
from django.core.validators import MinValueValidator, ValidationError
from django.db import models
from django.db.models import Count
from django.db.models.base import ModelBase
from django.utils import timezone
from django.urls import reverse

from recurrence.fields import RecurrenceField

from .util import dst_aware_to_dst_ignore
from core.models import ExtendedUser as User, PresetImage
from membership_file.util import user_to_member

# Models related to the Calendar-functionality of the application.
# @since 29 JUN 2019

# Not now, but a later time (used as a default value below)
def later_rounded():
    return now_rounded() + timezone.timedelta(hours=2)

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
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Recurrence information (e.g. a weekly event)
    # This means we do not need to store (nor create!) recurring activities separately
    recurrences = RecurrenceField(blank=True, default="")

    # Maximum number of participants/slots
    # -1 denotes unlimited
    max_slots = models.IntegerField(default=1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited slots")
    max_participants = models.IntegerField(default=-1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited participants")

    # Maximum number of slots that someone can join
    max_slots_join_per_participant = models.IntegerField(default=1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited slots")

    subscriptions_required = models.BooleanField(default=True,
        help_text="People are only allowed to go to the activity if they register beforehand")

    # Possible slot-creation options:
    # - Never: Slots can only be created in the admin panel
    # - Auto: Slots are created automatically. They are only actually created in the DB once a participant joins.
    #                                          Until that time they do look like real slots though (in the UI)
    # - Users: Slots can be created by users. Users can be the owner of at most max_slots_join_per_participant slots
    SLOT_CREATION_STAFF = "CREATION_NONE"
    SLOT_CREATION_AUTO = "CREATION_AUTO"
    SLOT_CREATION_USER = "CREATION_USER"
    slot_creation = models.CharField(
        max_length=15,
        choices=[
            (SLOT_CREATION_STAFF,   "Never/By Administrators"),
            (SLOT_CREATION_AUTO,   "Automatically"),
            (SLOT_CREATION_USER,   "By Users"),
        ],
        default='CREATION_AUTO',
    )

    # When people can start/no longer subscribe to slots
    subscriptions_open = models.DurationField(default=timezone.timedelta(days=7))
    subscriptions_close = models.DurationField(default=timezone.timedelta(hours=2))

    @property
    def image_url(self):
        if self.image is None:
            return f'{settings.STATIC_URL}images/activity_default.png'
        return self.image.image.url

    def get_all_activity_moments(self, start_date, end_date):
        """ Retrieves (or creates based on recurrences) all ActivityMoment instances in the given time frame """
        event_start_time = self.start_date.astimezone(timezone.get_current_timezone()).time()
        utc_start_time = self.start_date.time()

        # recurrence expects each EXDATE's time to match the event's start time (in UTC; ignores DST)
        # Why it doesn't store it that way in the first place remains a mystery
        self.recurrences.exdates = list(map(lambda dt:
                                       datetime.datetime.combine(timezone.localtime(dt).date(),
                                                        utc_start_time, tzinfo=timezone.utc),
                                            self.recurrences.exdates
                                       ))
        activity_moments = []

        recurrence_dts = self.recurrences.between(start_date, end_date, dtstart=self.start_date, inc=True)

        for occurence in recurrence_dts:
            # recurrence does not handle daylight-saving time! If we were to keep the occurence as is,
            # then summer events would occur an hour earlier in winter!
            occurence = timezone.get_current_timezone().localize(
                datetime.datetime.combine(timezone.localtime(occurence).date(), event_start_time)
            )
            try:
                activity_moment = ActivityMoment.objects.get(
                    recurrence_id=occurence,
                    parent_activity=self,
                )
            except ActivityMoment.DoesNotExist:
                activity_moment = ActivityMoment(
                    recurrence_id=occurence,
                    parent_activity=self,
                )
            activity_moments.append(activity_moment)

        # Get all moment objects that are not part of the defined recurrences
        single_activity_moments = ActivityMoment.objects.filter(
            parent_activity=self,
            recurrence_id__gte = start_date,
            recurrence_id__lte = end_date,
        ).exclude(
            recurrence_id__in = recurrence_dts
        )

        return activity_moments + [*single_activity_moments]

    # String-representation of an instance of the model
    def __str__(self):
        if self.is_recurring:
            return f"{self.title} (recurring)"
        return f"{self.title} (not recurring)"

    # Whether the activity is recurring
    @property
    def is_recurring(self):
        return bool(self.recurrences.rdates or self.recurrences.rrules)

    # Whether this activity has an occurence at a specific date
    def has_occurence_at(self, date, is_dst_aware=False):
        if not self.is_recurring:
            return date == self.start_date

        if not is_dst_aware:
            date = dst_aware_to_dst_ignore(date, self.start_date, reverse=True)
        occurences = self.get_occurences_between(date, date, dtstart=self.start_date, inc=True)
        return next(occurences, None) is not None

    def get_occurences_between(self, after, before, inc=False, dtstart=None, dtend=None, cache=False):
        dtstart = dtstart or self.start_date

        # the recurrences package does not work with DST. Since we want our activities
        # to ignore DST (E.g. events starting at 16.00 is summer should still start at 16.00
        # in winter, and vice versa), we have to account for the difference here.
        return map(lambda occurence: dst_aware_to_dst_ignore(occurence, dtstart), self.recurrences.between(after, before, inc=inc,
                dtstart=dtstart, dtend=dtend, cache=cache))     

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}
        exclude = exclude or []

        # Activities must start before they can end
        if 'start_date' not in exclude and 'end_date' not in exclude and self.start_date >= self.end_date:
            errors.update({'start_date': 'Start date must be before the end date'})

        if 'subscriptions_open' not in exclude and 'subscriptions_close' not in exclude:
            # Subscriptions must open before they close
            if self.subscriptions_open < self.subscriptions_close:
                errors.update({'subscriptions_open': 'Subscriptions must open before they can close'})

            # Ensure that subscriptions_open and subscriptions_close are a non-negative value
            if self.subscriptions_open < timezone.timedelta():
                errors.update({'subscriptions_open': 'Subscriptions must open before the activity starts'})

            if self.subscriptions_close < timezone.timedelta():
                errors.update({'subscriptions_close': 'Subscriptions must close before the activity starts'})

        r = self.recurrences
        if 'recurrences' not in exclude and r:
            recurrence_errors = []

            # Attempting to exclude dates if no recurrence is specified
            if not r.rrules and (r.exrules or r.exdates):
                recurrence_errors.append('Cannot exclude dates if the activity is non-recurring')

            if recurrence_errors:
                errors.update({'recurrences': recurrence_errors})

        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self, recurrence_id=None):
        """
        Returns the absolute url for the activity
        :param recurrence_id: Specifies the start-time and applies that in the url for recurrent activities
        :return: the url for the activity page
        """
        # There is currently no version of the object without recurrrence_id
        assert recurrence_id is not None

        return reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': self.id,
            'recurrence_id': recurrence_id
        })


class ActivityDuplicate(ModelBase):
    """
    Copy fields defined in local_fields automatically from Activity to ActivityMoment. This way any future changes
    is reflected in both the Activity and ActivityMoments and conflicts can not occur.
    """
    def __new__(mcs, name, bases, attrs, **kwargs):
        # Create the fields that are copied and can be tweaked from the Activity Model
        meta_class = attrs.get('Meta')
        if meta_class:
            for field_name in getattr(meta_class, 'copy_fields', []):
                # Generate the model fields
                for field in Activity._meta.fields:
                    if field.name == field_name:
                        new_field = copy.deepcopy(field)
                        new_field.blank = True
                        new_field.null = True
                        new_field.default = None

                        new_field_name = 'local_'+field_name
                        new_field.name = new_field_name

                        attrs[new_field_name] = new_field
                        break
                else:
                    raise KeyError(f"'{field_name}' is not a property on Activity")

                # Generate the method that retrieves correct values where necessary
                attrs[field_name] = property(mcs.generate_lookup_method(field_name))

            # Remove the attribute from the Meta class. It's been used and Django doesn't know what to do with it
            del meta_class.copy_fields

            for field_name in getattr(meta_class, 'link_fields', []):
                # Generate the method that retrieves correct values where necessary
                attrs[field_name] = property(mcs.generate_lookup_method(field_name))

            del meta_class.link_fields

        return super().__new__(mcs, name, bases, attrs, **kwargs)

    @classmethod
    def generate_lookup_method(cls, field_name):
        """ Generates a lookup method that for the given field_name looks in the objects local storage before looking
        in its parent_activity model instead for the given attribute """
        def get_activity_attribute(self):
            local_attr = getattr(self, 'local_'+field_name, None)
            if local_attr is None or local_attr == '':
                return getattr(self.parent_activity, field_name)
            return local_attr

        return get_activity_attribute


class ActivityMoment(models.Model, metaclass=ActivityDuplicate):
    parent_activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    recurrence_id = models.DateTimeField(verbose_name="parent activity date/time")

    created_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['parent_activity', 'recurrence_id']
        # Define the fields that can be locally be overwritten
        copy_fields = ['description', 'location', 'max_participants']
        # Define fields that are instantly looked for in the parent_activity
        # If at any point in the future these must become customisable, one only has to move the field name to the
        # copy_fields attribute
        link_fields = ['title', 'image']

    @property
    def start_time(self):
        return self.recurrence_id

    @property
    def end_time(self):
        return self.recurrence_id + (self.parent_activity.end_date - self.parent_activity.start_date)

    def get_subscribed_users(self):
        """ Returns a queryest of all USERS (not participants) in this activity moment """
        return User.objects.filter(
            participant__activity_slot__parent_activity_id=self.parent_activity_id,
            participant__activity_slot__recurrence_id=self.recurrence_id,
        ).distinct()

    def get_user_subscriptions(self, user):
        """
        Get all user subscriptions on this activity
        :param user: The user that needs to looked out for
        :return: Queryset of all participant entries
        """
        if user.is_anonymous:
            return Participant.objects.none()

        return Participant.objects.filter(
            activity_slot__parent_activity__id=self.parent_activity_id,
            activity_slot__recurrence_id=self.recurrence_id,
            user_id=user.id,
        )

    def get_slots(self):
        """
        Gets all slots for this activity moment
        :return: Queryset of all slots associated with this activity at this moment
        """
        return ActivitySlot.objects.filter(
            parent_activity__id=self.parent_activity_id,
            recurrence_id=self.recurrence_id,
        )

    def is_open_for_subscriptions(self):
        """
        Whether this activitymoment is open for subscriptions
        :return: Boolean
        """
        now = timezone.now()
        open_date_in_past = self.recurrence_id - self.parent_activity.subscriptions_open <= now
        close_date_in_future = self.recurrence_id - self.parent_activity.subscriptions_close >= now
        return open_date_in_past and close_date_in_future

    def get_absolute_url(self):
        """
        Returns the absolute url for the activity
        :return: the url for the activity page
        """

        return reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': self.parent_activity_id,
            'recurrence_id': self.recurrence_id,
        })


class ActivitySlot(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, null=True,
        help_text="If left empty, matches location with activity")
    start_date = models.DateTimeField(blank=True, null=True,
        help_text="If left empty, matches start date with activity")
    end_date = models.DateTimeField(blank=True, null=True,
        help_text="If left empty, matches end date with activity")

    # User that created the slot (or one that's in the slot if the original owner is no longer in the slot)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    # The activity that this slot belongs to
    # NB: The slot belongs to just a single _occurence_ of a (recurring) activity.
    #   Hence, we need to store both the foreign key and a date representing one if its occurences
    # TODO: Create a widget for the parent_activity_recurrence so editing is a bit more user-friendly
    parent_activity = models.ForeignKey(Activity, related_name="activity_slot_set", on_delete=models.CASCADE)
    recurrence_id = models.DateTimeField(blank=True, null=True,
        help_text="If the activity is recurring, set this to the date/time of one of its occurences. Leave this field empty if the parent activity is non-recurring.",
        verbose_name="parent activity date/time")

    participants = models.ManyToManyField(User, blank=True, through="Participant", related_name="participant_info")
    max_participants = models.IntegerField(default=-1, validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited participants", verbose_name="maximum number of participants")

    image = models.ForeignKey(PresetImage, blank=True, null=True, related_name="slot_image", on_delete=models.SET_NULL,
        help_text="If left empty, matches the image of the activity.")

    def __str__(self):
        return f"{self.id}"

    @property
    def image_url(self):
        if self.image is None:
            return self.parent_activity.image_url
        return self.image.image.url

    # Participants already subscribed
    def get_subscribed_participants(self):
        return self.participants

    # Number of participants already subscribed
    def get_num_subscribed_participants(self):
        return self.get_subscribed_participants().count()

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}
        exclude = exclude or []

        exclude_start_or_end = 'start_date' in exclude or 'end_date' in exclude

        if not exclude_start_or_end:
            # Activities must start before they can end
            if self.start_date and self.end_date and self.start_date >= self.end_date:
                errors.update({'start_date': 'Start date must be before the end date'})

        if 'parent_activity' not in exclude:
            if self.recurrence_id is None:
                # Must set a recurrence-ID if the parent activity is recurring
                if self.parent_activity.is_recurring:
                    errors.update({'recurrence_id': 'Must set a date/time as the parent activity is recurring'})
            else:
                # Must not set a recurrence-ID if the parent activity not is recurring
                if not self.parent_activity.is_recurring:
                    errors.update({'recurrence_id': 'Must NOT set a date/time as the parent activity is NOT recurring'})
                elif not self.parent_activity.has_occurence_at(self.recurrence_id):
                    errors.update({'recurrence_id': 'Parent activity has no occurence at the given date/time'})

            if not exclude_start_or_end:
                # Start/end times must be within start/end times of parent activity
                if self.start_date and self.start_date < self.parent_activity.start_date:
                    errors.update({'start_date': 'Start date cannot be before the start date of the parent activity'})
                if self.start_date and self.end_date > self.parent_activity.end_date:
                    errors.update({'end_date': 'End date cannot be after the end date of the parent activity'})

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': self.parent_activity.id,
            'recurrence_id': self.recurrence_id,
        })


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_slot = models.ForeignKey(ActivitySlot, on_delete=models.CASCADE)
    showed_up = models.BooleanField(null=True, default=None, help_text="Whether the participant actually showed up")

    def __str__(self):
        return self.user.get_simple_display_name()
