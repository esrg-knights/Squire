from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.urls import reverse

import django_ical.feedgenerator

from django_ical.utils import build_rrule_from_recurrences_rrule, build_rrule_from_text
from django_ical.views import ICalFeed
from django_ical.feedgenerator import ICal20Feed
from icalendar.cal import Timezone, TimezoneStandard, TimezoneDaylight

from .models import Activity
from .util import generate_vtimezone

# Monkey-patch; Why is this not open for extension in the first place?
django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP = (
    *(django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP),
    ('recurrenceid',    'recurrence-id'),
)


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
        tz_info = generate_vtimezone(settings.TIME_ZONE, datetime(2020, 1, 1))
        tz_info.add('x-lic-location', settings.TIME_ZONE)
        return tz_info

    #######################################################
    # Activities

    def items(self):
        # Only consider published activities
        return Activity.objects.filter(published_date__lte=timezone.now()).order_by('-published_date')

    def item_guid(self, item):
        # ID should be _globally_ unique
        return f"activity-id-{item.id}@kotkt.nl"
    
    def item_class(self, item):
        return "PUBLIC"

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_start_datetime(self, item):
        # Convert to Europe/Amsterdam to ensure daylight saving time is accounted for in recurring events
        return item.start_date.astimezone(timezone.get_current_timezone())
    
    def item_end_datetime(self, item):
        # Convert to Europe/Amsterdam to ensure daylight saving time is accounted for in recurring events
        return item.end_date.astimezone(timezone.get_current_timezone())
    
    def item_created(self, item):
        return item.created_date
    
    def item_updateddate(self, item):
        return item.last_updated_date

    def item_timestamp(self, item):
        # When the item was generated, which is at this moment!
        return timezone.now()

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
    def item_rrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.rrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    # Recurrence rules for dates to exclude
    def item_exrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.exrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    # Dates to include for recurrence rules
    def item_rdate(self, item):
        if item.recurrences:
            return item.recurrences.rdates

    # Dates to exclude for recurrence rules
    def item_exdate(self, item):
        if item.recurrences:
            # Each EXDATE's time needs to match the event start-time, but they default to midnigth in the widget!
            # Since there's no possibility to select the time in the UI either, we're overriding it here
            # and enforce each EXDATE's time to be equal to the event's start time
            event_start_time = item.start_date.astimezone(timezone.get_current_timezone()).time()
            item.recurrences.exdates = list(map(lambda dt:
                    timezone.get_current_timezone().localize(
                        datetime.combine(timezone.localtime(dt).date(),
                        event_start_time)
                    ),
                    item.recurrences.exdates
            ))
            return item.recurrences.exdates

    # RECURRENCE-ID
    def item_recurrenceid(self, item):
        return None

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
