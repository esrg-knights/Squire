from django.conf import settings
from django.utils import timezone

from django_ical.utils import build_rrule_from_recurrences_rrule
from django_ical.views import ICalFeed

from .models import Activity

class EventFeed(ICalFeed):
    """
    A simple event calender
    Please refer the docs for the full list of options:
    https://django-ical.readthedocs.io/en/latest/usage.html#property-reference-and-extensions
    """
    product_id = '-//Squire//Activity Calendar//EN'
    timezone = 'UTC'
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
        return self.item_created(item)

    def item_link(self, item):
        # There is no special page for the activity
        return ""

    def item_location(self, item):
        return item.location
    
    def item_status(self, item):
        # TODO: check how "CANCELLED" activiites show in Google Calendar and Outlook Calendar
        return item.status
    
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
            print(item.recurrences.exdates)
            # REEE dit is allemaal UTC!
            # TODO: kijk of er in de recurrence ding een optie UTC zit ofzo...
            # of convert de begin/eindtijd van events naar UTC in deze feed, en de timezone ook
            return item.recurrences.exdates
