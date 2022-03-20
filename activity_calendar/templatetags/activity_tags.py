import datetime

from django import template
from django.utils import timezone
from django.utils.formats import date_format

from activity_calendar.models import Activity, ActivityMoment
from membership_file.models import Member

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


@register.inclusion_tag("activity_calendar/snippet_activity_moment.html", takes_context=True)
def render_activity_block(context, activity_moment: ActivityMoment):

    show_signup_status = activity_moment.max_participants != 0 or activity_moment.subscriptions_required
    show_signup_status = show_signup_status and not activity_moment.slot_creation == Activity.SLOT_CREATION_NONE

    subscription_open_date = activity_moment.start_date - activity_moment.parent_activity.subscriptions_open
    if subscription_open_date < timezone.now():
        subscription_open_date = None

    context = {
        'activity_moment': activity_moment,
        'show_signup_status': show_signup_status,
        'member_is_subscribed': activity_moment.get_user_subscriptions(context['user']).exists(),
        'subscription_open_date': subscription_open_date
    }


    return context
