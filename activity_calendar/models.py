import copy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator, ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.formats import date_format
from django.urls import reverse
from recurrence.fields import RecurrenceField

import activity_calendar.util as util
from core.models import PresetImage
from core.fields import MarkdownTextField
from committees.utils import user_in_association_group
from membership_file.models import Member
from activity_calendar.constants import ActivityType, SlotCreationType, ActivityStatus
from activity_calendar.managers import MeetingManager


User = get_user_model()

#############################################################################
# Models related to the Calendar-functionality of the application.
# @since 29 JUN 2019
#############################################################################

__all__ = ["Activity", "ActivityMoment", "ActivitySlot", "Participant"]


# Rounds the current time (used as a default value below)
def now_rounded():
    return timezone.now().replace(minute=0, second=0)


class CoreActivityGrouping(models.Model):
    """
    A method to group certain core activities together. E.g. all boardgame evenings,
    all roleplay-related actitvities, LARP-stuff, etc.
    """

    identifier = models.CharField(max_length=127, unique=True)

    def __str__(self):
        return self.identifier + " (activity grouping)"


# The Activity model represents an activity in the calendar
class Activity(models.Model):
    class Meta:
        verbose_name_plural = "activities"
        permissions = [
            ("can_view_activity_participants_before", "[F] Can view an activity's participants before it starts."),
            ("can_view_activity_participants_during", "[F] Can view an activity's participants during it."),
            ("can_view_activity_participants_after", "[F] Can view an activity's participants after it has ended."),
            (
                "can_register_outside_registration_period",
                "[F] Can (de)register for activities if registrations are closed.",
            ),
            (
                "can_ignore_none_slot_creation_type",
                "[F] Can create slots for activities with slots that normally do not allow slot creation by users.",
            ),
            (
                "can_ignore_slot_creation_limits",
                "[F] Can create more slots even if the maximum amount of slots is reached.",
            ),
            ("can_select_slot_image", "[F] Can choose an alternative slot image when creating a slot."),
            (
                "can_view_private_slot_locations",
                "[F] Can view a slot's location even if they are marked as 'private' by the activity.",
            ),
            ("can_host_meetings", "[F] Can host meetings"),
            ("change_meeting_recurrences", "[F] Can adjust meeting recurrence rules"),
        ]

    markdown_images = GenericRelation("core.MarkdownImage")

    # The User that created the activity
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    organisers = models.ManyToManyField("committees.AssociationGroup", through="OrganiserLink")
    core_grouping = models.ForeignKey(CoreActivityGrouping, on_delete=models.SET_NULL, blank=True, null=True)

    # General information
    title = models.CharField(max_length=255)
    description = MarkdownTextField(
        help_text="Note that uploaded images are publicly accessible, even if the activity is unpublished.",
        null=True,
        blank=True,
    )
    location = models.CharField(max_length=255)
    slots_image = models.ForeignKey(
        PresetImage, blank=True, null=True, related_name="activity_image", on_delete=models.SET_NULL
    )
    promotion_image = models.ImageField(blank=True, null=True, upload_to="images/activity/%Y/%m/")
    file_folder = models.ForeignKey(
        "nextcloud_integration.SquireNextCloudFolder", blank=True, null=True, on_delete=models.SET_NULL
    )

    # Creation and last update dates (handled automatically)
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    # The date at which the activity will become visible for all users
    published_date = models.DateTimeField(default=now_rounded)

    # Start and end times
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    full_day = models.BooleanField(default=False, help_text="Whether this event marks the entire day")
    display_end_time = models.BooleanField(default=False, help_text="Whether the end time is displayed on the site")

    # Recurrence information (e.g. a weekly event)
    # This means we do not need to store (nor create!) recurring activities separately
    recurrences = RecurrenceField(blank=True, default="")

    # Maximum number of participants/slots
    # -1 denotes unlimited
    max_slots = models.IntegerField(
        default=1, validators=[MinValueValidator(-1)], help_text="-1 denotes unlimited slots"
    )
    max_participants = models.IntegerField(
        default=-1, validators=[MinValueValidator(-1)], help_text="-1 denotes unlimited participants"
    )

    # Maximum number of slots that someone can join
    max_slots_join_per_participant = models.IntegerField(
        default=1, validators=[MinValueValidator(-1)], help_text="-1 denotes unlimited slots"
    )

    private_slot_locations = models.BooleanField(
        default=False, help_text="Private locations are hidden for users not registered to the relevant slot"
    )

    subscriptions_required = models.BooleanField(
        default=False, help_text="People are only allowed to go to the activity if they register beforehand"
    )

    # Possible slot-creation options:
    # - Staff: Slots can only be created by organisers in the front-end or through the admin panel
    # - Auto: Slots are created automatically. They are only actually created in the DB once a participant joins.
    #                                          Until that time they do look like real slots though (in the UI)
    # - Users: Slots can be created by users. Users can be the owner of at most max_slots_join_per_participant slots
    # - No signup: No slots; users cannot sign up for this activity
    slot_creation = models.CharField(
        max_length=15,
        choices=[
            (SlotCreationType.SLOT_CREATION_STAFF, "By Organisers"),
            (SlotCreationType.SLOT_CREATION_AUTO, "Automatically"),
            (SlotCreationType.SLOT_CREATION_USER, "By Users"),
            (SlotCreationType.SLOT_CREATION_NONE, "No signup"),
        ],
        default=SlotCreationType.SLOT_CREATION_NONE,
    )

    # Possible activity types:
    # - Public: A normal activity of the association
    # - Meeting: Represents an internal meeting
    type = models.CharField(
        max_length=8,
        default=ActivityType.ACTIVITY_PUBLIC,
        choices=[
            (ActivityType.ACTIVITY_PUBLIC, "Public activity"),
            (ActivityType.ACTIVITY_MEETING, "Meeting"),
        ],
    )

    # When people can start/no longer subscribe to slots
    subscriptions_open = models.DurationField(default=timezone.timedelta(days=7))
    subscriptions_close = models.DurationField(default=timezone.timedelta(hours=2))

    @property
    def slots_image_url(self):
        if self.slots_image is None:
            return f"{settings.STATIC_URL}images/default_logo.png"
        return self.slots_image.image.url

    def get_activitymoments_between(self, start_date, end_date, exclude_removed=True):
        """
        Get a list of ActivityMoments, each representing an occurrence of this activity for which
        any point in that ActivityMoment's duration occurs between the specified start and end date.

        Note that an ActivityMoment is not entirely the same as an occurrence, as an ActivityMoment can
        have a different start time than the occurrence it represents. This is accounted for.

        :param start_date: The start datetime instance
        :param end_date: The end datetime instance
        :param exclude_removed: Whether activitymoments with status removed should not be included (default True)
        """
        # We should also include activities that start before "start_date", but also end after "start_date"
        #   (i.e., their start date is before the specified bounds, but their end date is within it).
        # Any occurrence before (start_date - duration) can never partially take place inside the
        #   specified time period, so there's no need to look back even further.
        activity_duration = self.duration
        recurrency_occurences = self.get_occurrences_starting_between(start_date - activity_duration, end_date)

        # Get the correct activitymoment instances from the database
        activity_moments_between_query = Q(recurrence_id__gte=(start_date - activity_duration)) & Q(
            recurrence_id__lte=end_date
        )
        # Get a list of all activitymoments that due to shift are either
        # incorrectly included (surplus) or wrongly excluded (extra)
        surplus_moments, extra_moments = self._get_queries_for_alt_start_time_activity_moments(start_date, end_date)

        # Filter out all activitymoments with an alt start time outside the bounds
        surplus_moments_queryset = self.activitymoment_set.filter(surplus_moments).values_list(
            "recurrence_id", flat=True
        )
        recurrency_occurences = filter(lambda occ: occ not in surplus_moments_queryset, recurrency_occurences)

        # Filter out removed activities
        removed_moments_queryset = self.activitymoment_set.filter(status=ActivityStatus.STATUS_REMOVED).values_list(
            "recurrence_id", flat=True
        )
        recurrency_occurences = filter(lambda occ: occ not in removed_moments_queryset, recurrency_occurences)

        # Fetch existing activitymoments
        #   They must either be within the bounds
        #   OR be extra ones due to different start/end date(s)
        query_filter = (activity_moments_between_query | extra_moments) & ~surplus_moments
        existing_moments = self.activitymoment_set
        if exclude_removed:
            existing_moments = existing_moments.exclude(status=ActivityStatus.STATUS_REMOVED)
        existing_moments = list(existing_moments.filter(query_filter))

        # Get occurrences for which we have no ActivityMoment
        unstored_recurrency_occurences = filter(
            lambda occ: all(existing_moment.recurrence_id != occ for existing_moment in existing_moments),
            recurrency_occurences,
        )

        # Generate new ActivityMoments for them
        unstored_recurrency_occurences = map(
            lambda occ: ActivityMoment(
                recurrence_id=occ,
                parent_activity=self,
            ),
            unstored_recurrency_occurences,
        )

        return list(unstored_recurrency_occurences) + existing_moments

    def _get_cancelled_activity_moments(self, include_cancelled=False, include_removed=True):
        """Returns all activitymoments queryset for this activity that are cancelled and/or removed"""
        query_cancelled = Q(status=ActivityStatus.STATUS_CANCELLED)
        query_removed = Q(status=ActivityStatus.STATUS_REMOVED)
        if include_cancelled and include_removed:
            return self.activitymoment_set.filter(query_cancelled | query_removed)
        elif not include_cancelled and include_removed:
            return self.activitymoment_set.filter(query_removed)
        elif include_cancelled and not include_removed:
            return self.activitymoment_set.filter(query_cancelled)
        # It shoudl include neither, so return nothing (can occur when chaining methods)
        return self.activitymoment_set.none()

    def get_next_activitymoment(self, dtstart=None, inc=False, exclude_removed=True, exclude_cancelled=False):
        """
        Returns the next activitymoment that will occur (if any)
        :param dtstart: The start datetime instance (if any) from which an occurence needs to be retrieved
        :param inc: Whether the startdate should be included
        :param exclude_removed: Whether activitymoments with status removed should not be included (default True)
        :param exclude_cancelled: Whether activitymoments with status cancelled should not be included (default False)
        :return: The activitymoment instance that will occur next
        """
        dtstart = timezone.localtime(dtstart)
        e_ext = "e" if inc else ""  # Search query for inclusion statement

        activity_moments = self.activitymoment_set
        if exclude_removed:
            activity_moments = activity_moments.exclude(status=ActivityStatus.STATUS_REMOVED)

        if exclude_cancelled:
            activity_moments = activity_moments.exclude(status=ActivityStatus.STATUS_CANCELLED)

        ### Check for activitymoments stored in the database ###
        # Check activity_moment by recurrence id
        next_activity_moment = (
            activity_moments.filter(**{"recurrence_id__gt" + e_ext: dtstart})
            .filter(local_start_date__isnull=True)
            .order_by("recurrence_id")
            .first()
        )

        # Check for local start date adjustments
        local_activity_moment = (
            activity_moments.filter(**{"local_start_date__gt" + e_ext: dtstart}).order_by("local_start_date").first()
        )

        # Compare through start dates, which take local changes into account
        if local_activity_moment is not None:
            if next_activity_moment is None or local_activity_moment.start_date < next_activity_moment.start_date:
                next_activity_moment = local_activity_moment

        ### Check for recurrence patterns ###

        # Get a list of activity_moments that are not allowed because they have been moved and will therefore
        # already have been detected with the local_start_date search
        excluded_activity_moments = (
            self.activitymoment_set.filter(**{"recurrence_id__gt" + e_ext: dtstart})
            .filter(local_start_date__isnull=False)
            .order_by("recurrence_id")
            .values_list("recurrence_id", flat=True)
        )

        cancelled_activity_moments = self._get_cancelled_activity_moments(
            include_cancelled=exclude_cancelled,
            include_removed=exclude_removed,
        ).values_list("recurrence_id", flat=True)

        recurrence_dtstart = dtstart
        next_recurrence = self._get_next_recurring_occurence(recurrence_dtstart, inc)
        while next_recurrence in excluded_activity_moments or next_recurrence in cancelled_activity_moments:
            next_recurrence = self._get_next_recurring_occurence(next_recurrence, False)

        if next_recurrence is not None:
            # Check if recurrence ids do not match for the activitymoment and the recurrent activity
            # otherwise it could be the current activity that has been postponed.
            if next_activity_moment is None or (
                next_activity_moment.start_date > next_recurrence
                and next_activity_moment.recurrence_id != next_recurrence
            ):
                next_activity_moment = ActivityMoment(
                    recurrence_id=next_recurrence,
                    parent_activity=self,
                )

        # print(f"with {dtstart} found {next_activity_moment.recurrence_id}")

        return next_activity_moment

    def _get_next_recurring_occurence(self, dtstart, inc=False):
        """
        Returns the next occurrence according to the recurring format.
        :param dtstart: The starttime of the search
        :param inc: Whether dtstart is included in the search
        :return: The next occurrence since `dtstart` according to this activity's recurrence schema
        """
        # The after function does not know the initial start date of the recurrent activities
        # So dtstart should be set to the activity start date not search start date
        next_recurrence = self.recurrences.after(dtstart, inc=inc, dtstart=timezone.localtime(self.start_date))
        # print(f"C: {next_recurrence} - {self.start_date} - {timezone.localtime(self.start_date)}"

        return next_recurrence

    # String-representation of an instance of the model
    def __str__(self):
        if self.is_recurring:
            return f"{self.title} (recurring)"
        return f"{self.title} (not recurring)"

    # Whether the activity is recurring
    @property
    def is_recurring(self):
        return bool(self.recurrences.rdates or self.recurrences.rrules)

    @property
    def duration(self):
        """Gets the duration of this activity"""
        return self.end_date - self.start_date

    def get_occurrence_at(self, date):
        """
        Whether this activity has an occurrence that starts at the specified time
        Note: This does not take shifts in starting moment into account!
        :param date: Datetime instance of the occurrence
        :return:
        """
        # An activitymoment with this recurrence_id already exists
        activitymoments = self.activitymoment_set.filter(recurrence_id=date)
        if activitymoments.count() == 1:
            return activitymoments.first()

        # An activitymoment for this occurrence might not exist yet
        if self.is_recurring:
            # Activity is recurring
            if list(self.get_occurrences_starting_between(date, date)):
                return ActivityMoment(
                    parent_activity=self,
                    recurrence_id=date,
                )
        elif date == self.start_date:
            # A non-recurring activity only has one occurrence
            return ActivityMoment(
                parent_activity=self,
                recurrence_id=date,
            )
        return None

    def _get_queries_for_alt_start_time_activity_moments(self, after, before):
        """
        Get two Q objects containing ActivityMoments with alternative start times, such
        that they do (not) occur between the specified bounds while they would (not) if
        they did not have an alternative start time.

        The former object represents ActivityMoments that do NOT occur between the
            specified bounds due to their new start/end date, while they normally would.
        The latter object represents ActivityMoments that DO occur between the
            specified bounds due to their new start/end date, while they normally would not.
        """
        activity_duration = self.duration

        ####################
        # Find all activity_moments whose recurrence_id is inside the bounds, but whose
        #   alternative start_date is NOT between these bounds
        ####################
        # Activitymoment has a local_end_date before 'after'
        alt_start_outside_bounds = Q(local_end_date__lt=after)

        # Activitymoment has a local_start_date after 'before'
        alt_start_outside_bounds |= Q(local_start_date__gt=before)

        # Activitymoment does not have a local_end_date,
        #   but the (local_start_date + activity_duration) < 'after'
        alt_start_outside_bounds |= Q(local_end_date__isnull=True, local_start_date__lt=(after - activity_duration))

        # Should normally occur within the specified bounds
        recurrence_id_between = Q(recurrence_id__gte=(after - activity_duration), recurrence_id__lte=before)
        surplus_activity_moments = recurrence_id_between & alt_start_outside_bounds

        ####################
        # Find all activity_moments that have an alternative start_date between the bounds, but whose
        #   recurrence_id is NOT between these bounds
        ####################
        # Activitymoment has a local_start_date within the bounds
        alt_start_inside_bounds = Q(local_start_date__gte=after, local_start_date__lte=before)

        # Activitymoment has no local_end_date,
        #   and has a local_start_date just before the bounds, making it end
        #   inside (or after) the bounds
        #   More specifically, (local_start_date + activity_duration) >= 'after'
        alt_start_inside_bounds |= Q(
            local_end_date__isnull=True,
            local_start_date__gte=(after - activity_duration),
            local_start_date__lt=after,
        )

        # Activitymoment has no local_start_date and normally starts before the bounds,
        #   but the local_end_date >= after
        alt_start_inside_bounds |= Q(local_start_date__isnull=True, recurrence_id__lt=after, local_end_date__gte=after)

        # Activitymoment has a local_start_date < after, and a local_end_date > after
        alt_start_inside_bounds |= Q(local_start_date__lte=after, local_end_date__gte=after)

        # Should normally NOT occur between the specified bounds
        recurrence_id_not_between = ~Q(recurrence_id__gte=(after - activity_duration), recurrence_id__lte=before)
        extra_activity_moments = recurrence_id_not_between & alt_start_inside_bounds

        # return as two separate query filters to be used later elsewhere
        return surplus_activity_moments, extra_activity_moments

    def get_occurrences_starting_between(self, after, before, **kwargs):
        """
        Get an iterable of dates, each representing an occurrence of this activity that STARTS
        between the specified start and end date.

        Note that this does not take an alternative start date of the occurrence's corresponding
        ActivityMoment into account.
        """
        dtstart = timezone.localtime(self.start_date)

        # Make a copy so we don't modify our own recurrence
        recurrences = copy.deepcopy(self.recurrences)

        # EXDATEs and RDATEs should match the event's start time, but in the recurrence-widget they
        #   occur at midnight!
        # Since there is no possibility to select the RDATE/EXDATE time in the UI either, we need to
        #   override their time here so that it matches the event's start time. Their timezone are
        #   also changed into that of the event's start date
        # print(f"pre: {recurrences.exdates}")
        recurrences.exdates = list(util.set_time_for_RDATE_EXDATE(recurrences.exdates, dtstart))
        # if recurrences.exdates:
        #     print(recurrences.exdates[0].tzinfo)

        recurrences.rdates = list(util.set_time_for_RDATE_EXDATE(recurrences.rdates, dtstart))

        # Get all occurrences according to the recurrence module
        occurences = recurrences.between(after, before, dtstart=dtstart, inc=True, **kwargs)
        return occurences

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}
        exclude = exclude or []

        # Activities must start before they can end
        if "start_date" not in exclude and "end_date" not in exclude and self.start_date >= self.end_date:
            errors.update({"start_date": "Start date must be before the end date"})

        if "subscriptions_open" not in exclude and "subscriptions_close" not in exclude:
            # Subscriptions must open before they close
            if self.subscriptions_open < self.subscriptions_close:
                errors.update({"subscriptions_open": "Subscriptions must open before they can close"})

            # Ensure that subscriptions_open and subscriptions_close are a non-negative value
            if self.subscriptions_open < timezone.timedelta():
                errors.update({"subscriptions_open": "Subscriptions must open before the activity starts"})

            if self.subscriptions_close < timezone.timedelta():
                errors.update({"subscriptions_close": "Subscriptions must close before the activity starts"})

        r = self.recurrences
        if "recurrences" not in exclude and r:
            recurrence_errors = []

            # Attempting to exclude dates if no recurrence is specified
            if not r.rrules and (r.exrules or r.exdates):
                recurrence_errors.append("Cannot exclude dates if the activity is non-recurring")

            # At most one RRULE (RFC 5545)
            if len(r.rrules) > 1:
                recurrence_errors.append(
                    f"Can add at most one recurrence rule, but got {len(r.rrules)} (Can still add multiple Recurring Dates)"
                )

            # EXRULEs (RFC 2445) are deprecated (per RFC 5545)
            if len(r.exrules) > 0:
                recurrence_errors.append(f"Exclusion Rules are unsupported (Exclusion Dates can still be used)")

            if recurrence_errors:
                errors.update({"recurrences": recurrence_errors})

        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self, recurrence_id=None):
        """
        Returns the absolute url for the activity
        :param recurrence_id: Specifies the start-time and applies that in the url for recurrent activities
        :return: the url for the activity page
        """
        if recurrence_id is None:
            # There is currently no version of the object without recurrrence_id
            if self.is_recurring:
                # The Django admin calls this method without any parameters for
                #   its "view on site" functionality.
                return None
            else:
                # If the activity is non-recurring, there's just a single occurrence we
                #   can link back to
                recurrence_id = self.start_date

        return reverse(
            "activity_calendar:activity_slots_on_day", kwargs={"activity_id": self.id, "recurrence_id": recurrence_id}
        )

    def is_organiser(self, user):
        for association_group in self.organisers.all():
            if user_in_association_group(user, association_group):
                return True
        return False


class ActivityDuplicate(ModelBase):
    """
    Copy fields defined in local_fields automatically from Activity to ActivityMoment. This way any future changes
    is reflected in both the Activity and ActivityMoments and conflicts can not occur.
    """

    def __new__(mcs, name, bases, attrs, **kwargs):
        # Create the fields that are copied and can be tweaked from the Activity Model
        meta_class = attrs.get("Meta")
        if meta_class:
            for field_name in getattr(meta_class, "copy_fields", []):
                # Generate the model fields
                for field in Activity._meta.fields:
                    if field.name == field_name:
                        new_field = copy.deepcopy(field)
                        new_field.blank = True
                        new_field.null = True
                        new_field.default = None

                        new_field_name = "local_" + field_name
                        new_field.name = new_field_name

                        attrs[new_field_name] = new_field
                        break
                else:
                    raise KeyError(f"'{field_name}' is not a property on Activity")

                # Generate the method that retrieves correct values where necessary
                attrs[field_name] = property(mcs.generate_lookup_method(field_name))

            # Remove the attribute from the Meta class. It's been used and Django doesn't know what to do with it
            del meta_class.copy_fields

            for field_name in getattr(meta_class, "link_fields", []):
                # Generate the method that retrieves correct values where necessary
                attrs[field_name] = property(mcs.generate_lookup_method(field_name))

            del meta_class.link_fields

        return super().__new__(mcs, name, bases, attrs, **kwargs)

    @classmethod
    def generate_lookup_method(cls, field_name):
        """Generates a lookup method that for the given field_name looks in the objects local storage before looking
        in its parent_activity model instead for the given attribute"""

        def get_activity_attribute(self):
            local_attr = getattr(self, "local_" + field_name, None)
            if local_attr is None or str(local_attr) == "":
                return getattr(self.parent_activity, field_name)
            return local_attr

        return get_activity_attribute


class ActivityMoment(models.Model, metaclass=ActivityDuplicate):
    objects = models.Manager()
    meetings = MeetingManager()

    parent_activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    recurrence_id = models.DateTimeField(verbose_name="parent activity date/time")

    created_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    markdown_images = GenericRelation("core.MarkdownImage")

    class Meta:
        unique_together = ["parent_activity", "recurrence_id"]
        # Define the fields that can be locally be overwritten
        copy_fields = [
            "title",
            "description",
            "promotion_image",
            "file_folder",
            "location",
            "max_participants",
            "subscriptions_required",
            "slot_creation",
            "private_slot_locations",
            "full_day",
        ]
        # Define fields that are instantly looked for in the parent_activity
        # If at any point in the future these must become customisable, one only has to move the field name to the
        # copy_fields attribute
        link_fields = ["slots_image_url", "subscriptions_required", "display_end_time"]

    # Alternative start/end date of the activity. If left empty, matches the start/end time
    #   of this OCCURRENCE.
    # Note that we're not doing this through copy_fields, as there is no reason to make a lookup
    #   the start/end date of the parent activity.
    local_start_date = models.DateTimeField(blank=True, null=True)
    local_end_date = models.DateTimeField(blank=True, null=True)

    # Define status

    status = models.CharField(
        max_length=5,
        choices=[
            (ActivityStatus.STATUS_NORMAL, "Normal proceeed"),
            (ActivityStatus.STATUS_CANCELLED, "Cancel, with notification"),
            (ActivityStatus.STATUS_REMOVED, "Remove"),
        ],
        default=ActivityStatus.STATUS_NORMAL,
    )

    @property
    def start_date(self):
        return self.local_start_date or self.recurrence_id

    @property
    def end_date(self):
        if self.local_end_date is not None:
            return self.local_end_date

        # Add the activity's normal duration to the event's start time
        return self.start_date + self.parent_activity.duration

    @property
    def participant_count(self):
        return self.get_subscribed_users().count() + self.get_guest_subscriptions().count()

    @property
    def is_part_of_recurrence(self):
        # A non-recurring activity cannot be part of a recurrence
        if not self.parent_activity.is_recurring:
            return False

        local_recurrence_id = self.recurrence_id
        # Get the next instance of the recurring activity, include the given date. So it should return the activity
        # itself. If not, than it is not part of the recurring activity
        recurrence_date = self.parent_activity.recurrences.after(
            local_recurrence_id, inc=True, dtstart=self.parent_activity.start_date
        )
        return recurrence_date == local_recurrence_id

    @property
    def is_cancelled(self):
        return self.status != ActivityStatus.STATUS_NORMAL

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}
        exclude = exclude or []

        if "local_end_date" not in exclude and self.local_end_date is not None:
            if self.local_end_date <= self.start_date:
                errors.update(
                    {
                        "local_end_date": "End date must be later than this occurrence's start date ("
                        + date_format(self.start_date, "Y-m-d, H:i")
                        + ")"
                    }
                )

        if errors:
            raise ValidationError(errors)

    def get_subscribed_users(self):
        """Returns a queryest of all USERS (not participants) in this activity moment"""
        return User.objects.filter(participant__in=self.get_user_subscriptions()).distinct()

    def get_guest_subscriptions(self):
        return Participant.objects.filter_guests_only().filter(
            activity_slot__parent_activitymoment_id=self.id,
        )

    def get_user_subscriptions(self, user=None):
        """
        Get all user subscriptions on this activity
        :param user: The user that needs to looked out for
        :return: Queryset of all participant entries
        """
        participants = Participant.objects.filter_users_only().filter(
            activity_slot__parent_activitymoment_id=self.id,
        )
        if user:
            if user.is_anonymous:
                return Participant.objects.none()
            else:
                participants = participants.filter(user=user)

        return participants

    def get_slots(self):
        """
        Gets all slots for this activity moment
        :return: Queryset of all slots associated with this activity at this moment
        """
        if not self.pk:
            # If the activitymoment wasn't created yet, it cannot have any slots.
            # Attempting to retrieve them anyway will raise a ValueError
            return ActivitySlot.objects.none()
        return self.activity_slot_set.all()

    def is_open_for_subscriptions(self):
        """
        Whether this activitymoment is open for subscriptions
        :return: Boolean
        """
        if self.is_cancelled:
            # A closed activity is never open for subscriptions
            return False

        now = timezone.now()
        open_date_in_past = self.start_date - self.parent_activity.subscriptions_open <= now
        close_date_in_future = self.start_date - self.parent_activity.subscriptions_close >= now
        return open_date_in_past and close_date_in_future

    def is_full(self):
        return self.get_subscribed_users().count() >= self.max_participants and self.max_participants != -1

    def get_absolute_url(self):
        """
        Returns the absolute url for the activity
        :return: the url for the activity page
        """

        return reverse(
            "activity_calendar:activity_slots_on_day",
            kwargs={
                "activity_id": self.parent_activity_id,
                "recurrence_id": self.recurrence_id,
            },
        )

    def __str__(self):
        return f"{self.title} @ {self.start_date}"


class ActivitySlot(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(
        max_length=255, blank=True, null=True, help_text="If left empty, matches location with activity"
    )
    start_date = models.DateTimeField(
        blank=True, null=True, help_text="If left empty, matches start date with activity"
    )
    end_date = models.DateTimeField(blank=True, null=True, help_text="If left empty, matches end date with activity")

    # User that created the slot (or one that's in the slot if the original owner is no longer in the slot)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    # The activitymoment that this slot belongs to
    parent_activitymoment = models.ForeignKey(
        ActivityMoment, related_name="activity_slot_set", on_delete=models.CASCADE
    )

    max_participants = models.IntegerField(
        default=-1,
        validators=[MinValueValidator(-1)],
        help_text="-1 denotes unlimited participants",
        verbose_name="maximum number of participants",
    )

    image = models.ForeignKey(
        PresetImage,
        blank=True,
        null=True,
        related_name="slot_image",
        on_delete=models.SET_NULL,
        help_text="If left empty, matches the image of the activity.",
    )

    @property
    def image_url(self):
        if self.image is None:
            return self.parent_activitymoment.slots_image_url
        return self.image.image.url

    def get_subscribed_users(self):
        return User.objects.filter(participant__in=self.participant_set.filter_users_only())

    def get_guest_subscriptions(self):
        return self.participant_set.filter_guests_only()

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        errors = {}
        exclude = exclude or []

        exclude_start_or_end = "start_date" in exclude or "end_date" in exclude

        if not exclude_start_or_end:
            # Activities must start before they can end
            if self.start_date and self.end_date and self.start_date >= self.end_date:
                errors.update({"start_date": "Start date must be before the end date"})

        if "parent_activitymoment" not in exclude:
            if not exclude_start_or_end:
                # Start/end times must be within start/end times of parent activity
                if self.start_date and self.start_date < self.parent_activitymoment.start_date:
                    errors.update({"start_date": "Start date cannot be before the start date of the parent activity"})
                if self.start_date and self.end_date > self.parent_activitymoment.end_date:
                    errors.update({"end_date": "End date cannot be after the end date of the parent activity"})

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "activity_calendar:activity_slots_on_day",
            kwargs={
                "activity_id": self.parent_activitymoment.parent_activity_id,
                "recurrence_id": self.parent_activitymoment.recurrence_id,
            },
        )


class ParticipantManager(models.Manager):
    def filter_guests_only(self):
        """Returns only particpant instances of guests"""
        return self.get_queryset().exclude(guest_name="")

    def filter_users_only(self):
        """Returns only particpant instances of users"""
        return self.get_queryset().filter(guest_name="")


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_slot = models.ForeignKey(ActivitySlot, on_delete=models.CASCADE)
    # Charfield for adding external users, this can only be done through admin.
    guest_name = models.CharField(max_length=123, default="", blank=True)
    showed_up = models.BooleanField(null=True, default=None, help_text="Whether the participant actually showed up")

    objects = ParticipantManager()

    def __str__(self):
        if self.guest_name:
            return self.guest_name + " (ext)"
        return str(self.user)


class OrganiserLink(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    association_group = models.ForeignKey("committees.AssociationGroup", on_delete=models.CASCADE)
    archived = models.BooleanField(default=False)


class Calendar(models.Model):
    """Symbolises a calendar with certain activities"""

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(verbose_name="url string", help_text="The local url string", unique=True)
    description = models.CharField(max_length=256)

    activities = models.ManyToManyField(Activity, through="CalendarActivityLink")

    def __str__(self):
        return self.name


class CalendarActivityLink(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.calendar} - {self.activity}"


class MemberCalendarSettings(models.Model):
    member = models.OneToOneField(Member, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)

    use_birthday = models.BooleanField(default=False, verbose_name="Display my birthday in Knights birthday calendar")

    def __str__(self):
        return f"calendar settings for {self.member}: {self.use_birthday}"
