import datetime

from django import template
from django.utils import timezone
from django.utils.formats import date_format

from activity_calendar.models import Activity

register = template.Library()

@register.filter
def get_next_activity_instances(activity: Activity, max=3):
    next_activity_moments = []
    start_date = timezone.now()
    for i in range(max):
        next_activity = activity.get_next_activitymoment(dtstart=start_date)
        if next_activity is None:
            break
        start_date = next_activity.start_date
        next_activity_moments.append(next_activity)

    return next_activity_moments
