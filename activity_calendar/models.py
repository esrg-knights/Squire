from django.conf import settings
from django.db import models
from django.utils import timezone

from django_ical.utils import build_rrule_from_recurrences_rrule
from django_ical.views import ICalFeed
from recurrence.fields import RecurrenceField

# Models related to the Calendar-functionality of the application.
# @since 29 JUN 2019

# The Activity model represents an activity in the calendar
class Activity(models.Model): #TODO: Create testcases
    # The User that created the activity
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Possible statuses of an event
    STATUS_OPTIONS = [
        ("CONFIRMED",   "Confirmed"),
        ("CANCELLED",   "Cancelled"),
        ("TENTATIVE",   "Tentative"),
    ]

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=15, choices=STATUS_OPTIONS)
    
    # Creation and last update dates (handled automatically)
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    
    # The date at which the activity will become visible for all users
    published_date = models.DateTimeField(default=timezone.now)

    # Start and end times
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)

    # Recurrence information (e.g. a weekly event)
    recurrences = RecurrenceField()

    # Publishes the activity, making it visible for all users
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    # String-representation of an instance of the model
    def __str__(self):
        return "{1} ({0})".format(self.id, self.title)


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
        return item.status
    
    def item_transparency(self, item):
        # Items marked as "TRANSPARENT" show up as 'free' in busy time searches
        # Items marked as "OPAQUE" show up as 'busy' in busy time searches.
        return "TRANSPARENT"

    def item_rrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.rrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    def item_exrule(self, item):
        if item.recurrences:
            rules = []
            for rule in item.recurrences.exrules:
                rules.append(build_rrule_from_recurrences_rrule(rule))
            return rules

    def item_rdate(self, item):
        if item.recurrences:
            return item.recurrences.rdates

    def item_exdate(self, item):
        if item.recurrences:
            return item.recurrences.exdates
