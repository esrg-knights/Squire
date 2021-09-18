from datetime import datetime

from django.conf import settings
from django.utils import timezone

import django_ical.feedgenerator

from django_ical.utils import build_rrule_from_recurrences_rrule
from django_ical.views import ICalFeed
from django_ical.feedgenerator import ICal20Feed

from .models import Activity, ActivityMoment
import activity_calendar.util as util

# Monkey-patch; Why is this not open for extension in the first place?
django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP = (
    *(django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP),
    ('recurrenceid',    'recurrence-id'),
)

def only_for(class_type, default=None):
    def only_for_decorator(func):
        def func_wrapper(self, item):
            if isinstance(item, class_type):
                return func(self, item)
            return default
        return func_wrapper
    return only_for_decorator


class ExtendedICal20Feed(ICal20Feed):
    """
    iCalendar 2.0 Feed implementation that also supports VTIMEZONE.
    """

    def write_items(self, calendar):
        """
        Writes the feed to the specified file in the
        specified encoding.
        """
        tz_info = self.feed.get('vtimezone')
        if tz_info:
            calendar.add_component(tz_info)

        super().write_items(calendar)


class CESTEventFeed(ICalFeed):
    """
    A simple event calender
    Please refer the docs for the full list of options:
    https://django-ical.readthedocs.io/en/latest/usage.html#property-reference-and-extensions
    """
    feed_type = ExtendedICal20Feed

    product_id = '-//Squire//Activity Calendar//EN'
    file_name = "knights-calendar.ics"

    # Quick overwrite to allow results to be printed in the browser instead
    # Good for testing
    # def __call__(self, *args, **kwargs):
    #     response = super(CESTEventFeed, self).__call__(*args, **kwargs)
    #     from django.http import HttpResponse
    #     return HttpResponse(content=response._container, content_type='text')

    def title(self):
        # TODO: unhardcode
        return "Activiteiten Agenda - Knights"

    def description(self):
        # TODO: unhardcode
        return "Knights of the Kitchen Table Activiteiten en Evenementen."

    def method(self):
        return "PUBLISH"

    def timezone(self):
        return settings.TIME_ZONE

    #######################################################
    # Timezone information (Daylight-saving time, etc.)
    def vtimezone(self):
        tz_info = util.generate_vtimezone(settings.TIME_ZONE, datetime(2020, 1, 1))
        tz_info.add('x-lic-location', settings.TIME_ZONE)
        return tz_info

    #######################################################
    # Activities

    def items(self):
        # Only consider published activities
        activities = Activity.objects.filter(published_date__lte=timezone.now()).order_by('-published_date')
        exceptions = ActivityMoment.objects.filter(parent_activity__published_date__lte=timezone.now())

        return [*activities, *exceptions]

    def item_guid(self, item):
        # ID should be _globally_ unique
        if isinstance(item, Activity):
            activity_id = item.id
        elif isinstance(item, ActivityMoment):
            activity_id = item.parent_activity_id

        return f"local_activity-id-{activity_id}@kotkt.nl"

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
        return start_dt.astimezone(timezone.get_current_timezone())

    def item_end_datetime(self, item):
        # Convert to Europe/Amsterdam to ensure daylight saving time is accounted for in recurring events
        end_dt = item.end_date
        return end_dt.astimezone(timezone.get_current_timezone())

    def item_created(self, item):
        return item.created_date

    @only_for(ActivityMoment)
    def item_updateddate(self, item):
        return item.last_updated

    def item_timestamp(self, item):
        # When the item was generated, which is at this moment!
        return timezone.now()

    @only_for(ActivityMoment, default="/calendar/")
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
        if item.recurrences:
            return list(util.set_time_for_RDATE_EXDATE(item.recurrences.exdates, item.start_date))

    # RECURRENCE-ID
    @only_for(ActivityMoment)
    def item_recurrenceid(self, item):
        return item.recurrence_id.astimezone(timezone.get_current_timezone())

    # Include
    def feed_extra_kwargs(self, obj):
        kwargs = super().feed_extra_kwargs(obj)
        val = self._get_dynamic_attr('vtimezone', obj)
        if val:
            kwargs['vtimezone'] = val
        return kwargs

    # We also want to store the recurrence-id
    def item_extra_kwargs(self, item):
        kwargs = super().item_extra_kwargs(item)

        val =  self._get_dynamic_attr('item_recurrenceid', item)
        if val:
            kwargs['recurrenceid'] = val
        return kwargs
