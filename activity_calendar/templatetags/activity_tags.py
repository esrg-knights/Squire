from django import template
from django.utils import timezone
from django.template.defaultfilters import date as format_date

from activity_calendar.constants import SlotCreationType
from activity_calendar.models import Activity, ActivityMoment


register = template.Library()


@register.filter
def get_next_activity_instances(activity: Activity, start_dt=None, max=3):
    """
    Reutrns the next x activities for a given activity instances based on the start_time
    :param activity:
    :param start_dt: The start datetime, uses current time if None
    :param max:
    :return:
    """
    next_activity_moments = []
    start_date = start_dt or timezone.now()
    for i in range(max):
        next_activity = activity.get_next_activitymoment(dtstart=start_date)
        if next_activity is None:
            break
        try:
            if next_activity.start_date == next_activity_moments[-1].start_date:
                # Object returned is the same as last one, so break the sequence
                # This can occur on recurring events with an end date set or a max number of instances
                break
        except IndexError:
            pass
        start_date = next_activity.start_date
        next_activity_moments.append(next_activity)

    return next_activity_moments


@register.inclusion_tag("activity_calendar/snippet_activity_moment.html", takes_context=True)
def render_activity_block(context, activity_moment: ActivityMoment):
    show_signup_status = activity_moment.max_participants != 0 or activity_moment.subscriptions_required
    show_signup_status = show_signup_status and activity_moment.slot_creation != SlotCreationType.SLOT_CREATION_NONE

    subscription_open_date = activity_moment.start_date - activity_moment.parent_activity.subscriptions_open
    if subscription_open_date < timezone.now():
        subscription_open_date = None

    context = {
        "activity_moment": activity_moment,
        "show_signup_status": show_signup_status,
        "member_is_subscribed": activity_moment.get_user_subscriptions(context["user"]).exists(),
        "subscription_open_date": subscription_open_date,
    }

    return context


@register.filter
def readable_activity_datetime(activity_moment):
    """
    Converts the start and possible end time for a given activity_moment to a human readable form
    :param activity_moment: The activity_moment for which the occurrence time needs to be displayed
    :return:
    """
    # Database entries are stored in non-timezone format. Make sure it is in the right timezone format
    # This is normally done by the template engine date filter, but calling it in code circumvents that
    start_date = timezone.template_localtime(activity_moment.start_date)
    end_date = timezone.template_localtime(activity_moment.end_date)

    format_str = "l j E"
    if not activity_moment.full_day:
        format_str += " H:i"
    formatted_result = format_date(start_date, format_str)

    if activity_moment.display_end_time:
        if activity_moment.start_date.date() == activity_moment.end_date.date():
            format_str = ""
        else:
            format_str = "l j E"
        if not activity_moment.full_day:
            format_str += " H:i"

        if format_str != "":
            formatted_result += f" - {format_date(end_date, format_str).strip()}"

    return formatted_result
