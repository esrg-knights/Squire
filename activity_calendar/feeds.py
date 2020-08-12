from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

import django_ical.feedgenerator

from django_ical.utils import build_rrule_from_recurrences_rrule, build_rrule_from_text
from django_ical.views import ICalFeed
from django_ical.feedgenerator import ICal20Feed, FEED_FIELD_MAP
from icalendar.cal import Timezone, TimezoneStandard, TimezoneDaylight

from .models import Activity

# Monkey-patch; Why is this not open for extension in the first place?
django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP = (
    *(django_ical.feedgenerator.ITEM_EVENT_FIELD_MAP),
    ('recurrenceid',    'recurrence-id'),
)


ICAL_VTIMEZONE_FIELDS_MAP = [
    ("x_lic_location", 'x-lic-location'),
    ("tz_id",           'tzid')
]

ICAL_DAYLIGHT_FIELDS_MAP = [
    ("tzoffset_from", 'tzoffsetfrom'),
    ("tzoffset_to", 'tzoffsetto'),
    ("tzname", 'tzname'),
    ("dtstart", 'dtstart'),
    ("rrule", 'rrule'),
]

ICAL_VTIMEZONE_ITEMS_MAP = [
    ("daylight", TimezoneStandard),
    ("standard", TimezoneDaylight),
]

class ExtendedICal20Feed(ICal20Feed):
    """
    iCalendar 2.0 Feed implementation that also supports VTIMEZONE.
    """

    mime_type = "text/calendar; charset=utf8"

    def write_items(self, calendar):
        """
        Writes the feed to the specified file in the
        specified encoding.
        """
        tz_info = Timezone()
        for ifield, efield in ICAL_VTIMEZONE_FIELDS_MAP:
            val = self.feed.get(ifield)
            if val is not None:
                tz_info.add(efield, val)
        
        for ifield, tz_class in ICAL_VTIMEZONE_ITEMS_MAP:
            is_present = self.feed.get(ifield)
            if val:
                tz_dst = tz_class()
                for idaylightfield, efield in ICAL_DAYLIGHT_FIELDS_MAP:
                    val = self.feed.get(ifield + "_" + idaylightfield)
                    if val is not None:
                        tz_dst.add(efield, val)
                tz_info.add_component(tz_dst)

        calendar.add_component(tz_info)

        # print("Items:")
        # print(self.items)
        print("Feed:")
        print(self.feed)

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
    def vtimezone_x_lic_location(self):
        return settings.TIME_ZONE
    
    vtimezone_tz_id = settings.TIME_ZONE

    # Summer Time
    vtimezone_daylight_tzoffset_from = timedelta(hours=1)
    vtimezone_daylight_tzoffset_to = timedelta(hours=2)
    vtimezone_daylight_tzname = "CEST"
    vtimezone_daylight_dtstart = datetime(1970, 3, 29, 20)
    vtimezone_daylight_rrule = build_rrule_from_text("FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU")

    # Winter Time
    vtimezone_standard_tzoffset_from = timedelta(hours=2)
    vtimezone_standard_tzoffset_to = timedelta(hours=1)
    vtimezone_standard_tzname = "CET"
    vtimezone_standard_dtstart = datetime(1970, 10, 25, 3)
    vtimezone_standard_rrule = build_rrule_from_text("FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU")

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
        return item.start_date
    
    def item_end_datetime(self, item):
        return item.end_date
    
    def item_created(self, item):
        return item.created_date
    
    def item_updateddate(self, item):
        return item.last_updated_date

    def item_timestamp(self, item):
        # When the item was generated, which is at this moment!
        return timezone.now()

    def item_link(self, item):
        # There is no special page for the activity
        return ""

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
            utc_start_time = item.start_date.astimezone(timezone.utc).time()
            item.recurrences.exdates = list(map(lambda dt:
                    datetime.combine(
                        timezone.localtime(dt).date(),
                        utc_start_time, timezone.utc), item.recurrences.exdates))
            return item.recurrences.exdates

    # RECURRENCE-ID
    def item_recurrenceid(self, item):
        return None

    # Include 
    def feed_extra_kwargs(self, obj):
        kwargs = super().feed_extra_kwargs(obj)
        # x-lic-location
        for (field, _) in ICAL_VTIMEZONE_FIELDS_MAP:
            val = self._get_dynamic_attr("vtimezone_" + field, obj)
            if val:
                kwargs[field] = val

        # Daylight-saving items
        for (field, _) in ICAL_VTIMEZONE_ITEMS_MAP:
            # Daylight-saving item fields
            for (daylight_field, _) in ICAL_DAYLIGHT_FIELDS_MAP:
                val = self._get_dynamic_attr("vtimezone_" + field + "_" + daylight_field, obj)
                if val:
                    kwargs[field + "_" + daylight_field] = val
                    kwargs[field] = True

        return kwargs

    # We also want to store the recurrence-id
    def item_extra_kwargs(self, item):
        kwargs = super().item_extra_kwargs(item)

        recurrence_id =  self._get_dynamic_attr('item_recurrenceid', item)
        if recurrence_id:
            return {**kwargs, 'recurrenceid': recurrence_id}
        return kwargs
