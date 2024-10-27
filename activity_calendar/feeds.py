import recurrence

from datetime import datetime, date, timedelta

from django.conf import settings
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from django_ical import feedgenerator
from django_ical.feedgenerator import ICal20Feed
from django_ical.utils import build_rrule_from_recurrences_rrule
from django_ical.views import ICalFeed

from membership_file.models import Member

from .models import Activity, ActivityMoment, Calendar
from .constants import ActivityStatus, ActivityType
import activity_calendar.util as util


def only_for(class_type, default=None):
    def only_for_decorator(func):
        def func_wrapper(self, item):
            if isinstance(item, class_type):
                return func(self, item)
            return default

        return func_wrapper

    return only_for_decorator


def get_feed_id(item):
    # ID should be _globally_ unique
    if isinstance(item, Activity):
        return f"local_activity-name-{item.id}@kotkt.nl"
    elif isinstance(item, ActivityMoment):
        if item.is_part_of_recurrence:
            # To override an recurrence, the UID needs to be the same as the activity
            return f"local_activity-name-{item.parent_activity.id}@kotkt.nl"
        else:
            return f"local_activity-name-{item.parent_activity.id}-special-{item.id}@kotkt.nl"

    raise RuntimeError(f"An incorrect object instance has entered the calendar feed: {item.__class__.__name__}")


class ExtendedICal20Feed(ICal20Feed):
    """
    iCalendar 2.0 Feed implementation that also supports VTIMEZONE.
    """

    def write_items(self, calendar):
        """
        Writes the feed to the specified file in the
        specified encoding.
        """
        tz_info = self.feed.get("vtimezone")
        if tz_info:
            calendar.add_component(tz_info)

        super().write_items(calendar)


# Activities should only be processed if either it is recurring or it is non-recurring, but the activitymoment
# object has not yet been created. Otherwise it would yield two calendar activity copies
# as described in issue #213
def recurring_activities(activities):
    """Generator for activities to exclude invalid activity instances"""
    for activity in activities:
        if activity.is_recurring:
            yield activity
        elif not activity.activitymoment_set.exists():
            yield activity


class CESTEventFeed(ICalFeed):
    """
    A simple event calender
    Please refer the docs for the full list of options:
    https://django-ical.readthedocs.io/en/latest/usage.html#property-reference-and-extensions
    """

    feed_type = ExtendedICal20Feed

    product_id = "-//Squire//Activity Calendar//EN"
    file_name = "knights-calendar.ics"

    calendar_title = None
    calendar_description = None

    # Quick overwrite to allow results to be printed in the browser instead
    # Good for testing
    # def __call__(self, *args, **kwargs):
    #     response = super(CESTEventFeed, self).__call__(*args, **kwargs)
    #     from django.http import HttpResponse

    #     return HttpResponse(content=response._container, content_type="text")

    def title(self):
        if self.calendar_title is None:
            raise KeyError(f"'calendar_title' for {self.__class__.__name__} has not been defined.")
        return self.calendar_title

    def description(self):
        if self.calendar_description is None:
            raise KeyError(f"'calendar_description' for {self.__class__.__name__} has not been defined.")
        return self.calendar_description

    def method(self):
        return "PUBLISH"

    def timezone(self):
        return settings.TIME_ZONE

    #######################################################
    # Timezone information (Daylight-saving time, etc.)
    def vtimezone(self):
        tz_info = util.ical_timezone_factory.generate_vtimezone(settings.TIME_ZONE)
        return tz_info

    #######################################################
    # Activities

    def items(self):
        raise NotImplementedError(
            "This has not yet been implemented. " "Overwrite items() to add the activity gathering logic."
        )

    def item_guid(self, item):
        return get_feed_id(item)

    def item_class(self, item):
        return "PUBLIC"

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # Note that we're explicitly not converting the Markdown to HTML, as calendar
        #   applications do not all handle HTML in the same way (or at all). While it
        #   would be possible to remove all HTML tags from the rendered Markdown, this
        #   causes some text to lose meaning (E.g. "click [here](www.example.com)" becomes "click here").
        #   As Markdown is human-readable enough, we just return plain Markdown.
        return item.description

    def item_start_datetime(self, item):
        # Convert to Europe/Amsterdam to ensure daylight saving time is accounted for in recurring events
        start_dt = item.start_date
        start_dt = start_dt.astimezone(timezone.get_current_timezone())

        if item.full_day:
            # If full day, return this as a date instance instead
            return start_dt.date()
        else:
            return start_dt

    def item_end_datetime(self, item):
        # Convert to Europe/Amsterdam to ensure daylight saving time is accounted for in recurring events
        end_dt = item.end_date
        end_dt = end_dt.astimezone(timezone.get_current_timezone())

        if item.full_day:
            # If full day, return this as a date instance instead
            # Return date must be a day further as it is interpreted at 0:00 instead of 24:00
            return end_dt.date() + timedelta(days=1)
        else:
            return end_dt

    def item_created(self, item):
        return item.created_date

    @only_for(ActivityMoment)
    def item_updateddate(self, item):
        return item.last_updated

    def item_timestamp(self, item):
        # When the item was generated, which is at this moment!
        return timezone.now()

    @only_for(ActivityMoment)
    def item_status(self, item):
        if item.is_cancelled:
            return "CANCELLED"
        else:
            return "CONFIRMED"

    @only_for(ActivityMoment, default=reverse_lazy("activity_calendar:activity_upcoming"))
    def item_link(self, item):
        # The local url to the activity
        return item.get_absolute_url()

    def item_location(self, item):
        return item.location

    def item_transparency(self, item):
        # Items marked as "TRANSPARENT" show up as 'free' in busy time searches
        # Items marked as "OPAQUE" show up as 'busy' in busy time searches.
        return "TRANSPARENT"

    # Recurrence rules for dates to include
    # E.g. repeat the activity every 3rd wednesday of the month, repeat
    # every 2 weeks, etc.
    @only_for(Activity)
    def item_rrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.rrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    # Recurrence rules for dates to exclude
    @only_for(Activity)
    def item_exrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.exrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    # Dates to include for recurrence rules
    @only_for(Activity)
    def item_rdate(self, item):
        if item.recurrences:
            return list(util.set_time_for_RDATE_EXDATE(item.recurrences.rdates, item.start_date))

    # Dates to exclude for recurrence rules
    @only_for(Activity)
    def item_exdate(self, item):
        exclude_dates = []
        if item.recurrences:
            # The RDATES in the recurrency module store only dates and not times, so we need to address that
            exclude_dates += list(util.set_time_for_RDATE_EXDATE(item.recurrences.exdates, item.start_date))

        if item.pk:
            # Some feeds create activities on the fly (e.g. BirthdayCalendarFeed)
            # Those activities cannot retrieve their corresponding activitymoments, it'll cause a ValueError
            # Since these activities won't have activitymoments anyway, we can skip this step for them
            cancelled_moments = item.activitymoment_set.filter(status=ActivityStatus.STATUS_REMOVED).values_list(
                "recurrence_id", flat=True
            )
            tz = timezone.get_current_timezone()
            exclude_dates += filter(
                lambda occ: occ not in exclude_dates,
                map(lambda occ: occ.astimezone(tz), cancelled_moments),
            )

        # If there are no exclude_dates, don't bother including it in the icalendar file
        return exclude_dates or None

    # RECURRENCE-ID
    @only_for(ActivityMoment)
    def item_recurrence_id(self, item):
        if item.is_part_of_recurrence:
            return item.recurrence_id.astimezone(timezone.get_current_timezone())
        return None

    # Include
    def feed_extra_kwargs(self, obj):
        kwargs = super().feed_extra_kwargs(obj)
        val = self._get_dynamic_attr("vtimezone", obj)
        if val:
            kwargs["vtimezone"] = val
        return kwargs

    # We also want to store the recurrence-id
    def item_extra_kwargs(self, item):
        kwargs = super().item_extra_kwargs(item)

        val = self._get_dynamic_attr("item_recurrence_id", item)
        if val:
            kwargs["recurrence_id"] = val
        return kwargs


class PublicCalendarFeed(CESTEventFeed):
    """Define the feed for the public calendar"""

    product_id = "-//Squire//Activity Calendar//EN"
    file_name = "knights-calendar.ics"
    calendar_title = "ESRG Knights of the Kitchen Table"
    calendar_description = "Activities and events for ESRG Knights of the Kitchen Table."

    def items(self):
        # Only consider published activities
        activities = (
            Activity.objects.filter(published_date__lte=timezone.now())
            .order_by("-published_date")
            .filter(type=ActivityType.ACTIVITY_PUBLIC)
        )
        exceptions = ActivityMoment.objects.filter(parent_activity__in=activities).exclude(
            status=ActivityStatus.STATUS_REMOVED
        )

        return [*recurring_activities(activities), *exceptions]


class CustomCalendarFeed(CESTEventFeed):
    file_name = "knights-calendar.ics"

    @property
    def product_id(self):
        return f"-//Squire//Activity Calendar {self.calendar.name}//EN"

    def __call__(self, *args, **kwargs):
        self.calendar = get_object_or_404(Calendar, slug=kwargs["calendar_slug"])
        self.calendar_title = self.calendar.name
        self.calendar_description = self.calendar.description

        return super(CustomCalendarFeed, self).__call__(*args, **kwargs)

    def items(self):
        activities = self.calendar.activities.filter(published_date__lte=timezone.now()).order_by("-published_date")
        exceptions = ActivityMoment.objects.filter(parent_activity__in=activities).exclude(
            status=ActivityStatus.STATUS_REMOVED
        )

        return [*recurring_activities(activities), *exceptions]


class BirthdayCalendarFeed(CESTEventFeed):
    product_id = "-//Squire//Birthday Calendar//EN"
    file_name = "knights-birthday-calendar.ics"
    calendar_title = "Birthday calendar - Knights"
    calendar_description = "Knights of the Kitchen Table Birthday Calendar."

    @classmethod
    def construct_birthday(cls, member):
        """Constructs the birthday for the given member"""
        recurrence_pattern = recurrence.Recurrence(rrules=[recurrence.Rule(recurrence.YEARLY)])
        start_time = datetime.combine(
            member.date_of_birth, datetime.min.time(), tzinfo=timezone.get_current_timezone()
        )
        activity = Activity(
            title=f"It's {member.get_full_name()}'s birthday!",
            full_day=True,
            start_date=start_time,
            end_date=start_time,
            recurrences=recurrence_pattern,
        )
        # Declare a feed name
        activity.feed_id = f"bday-{slugify(member.get_full_name())}"
        return activity

    def items(self):
        """Constructs a list of activities that represent the birthdays of the members"""
        # Create iterator that builds activities from the list of members
        return map(
            self.construct_birthday,
            Member.objects.filter(
                memberyear__is_active=True,
                membercalendarsettings__use_birthday=True,
                date_of_birth__isnull=False,
            ),
        )

    def item_guid(self, item):
        return item.feed_id

    def item_link(self, item):
        return ""  # There is no page for a birthday

    def item_end_datetime(self, item):
        return item.start_date.date()
