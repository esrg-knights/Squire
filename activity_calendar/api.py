from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_safe
from django.http import HttpResponseBadRequest

from .models import Activity


def get_json_from_activity_moment(activity_moment, user=None):
    return {
        'groupId': activity_moment.parent_activity.id,
        'title': activity_moment.title,
        'description': activity_moment.description.as_rendered(),
        'location': activity_moment.location,
        # use urlLink instead of url as that creates unwanted interactions with the calendar js module
        'urlLink': activity_moment.get_absolute_url(),
        'recurrenceInfo': {
            'rrules': [rule.to_text() for rule in activity_moment.parent_activity.recurrences.rrules],
            'exrules': [rule.to_text() for rule in activity_moment.parent_activity.recurrences.exrules],
            'rdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity_moment.parent_activity.recurrences.rdates],
            'exdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity_moment.parent_activity.recurrences.exdates],
        },
        'subscriptionsRequired': activity_moment.parent_activity.subscriptions_required,
        'numParticipants': activity_moment.participant_count,
        'maxParticipants': activity_moment.max_participants,
        'isSubscribed': activity_moment.get_user_subscriptions(user).exists(),
        'canSubscribe': activity_moment.is_open_for_subscriptions(),
        'start': activity_moment.start_date.isoformat(),
        'recurrence_id': activity_moment.recurrence_id.isoformat(),
        'end': activity_moment.end_date.isoformat(),
        'allDay': False,
    }

@require_safe
def fullcalendar_feed(request):
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    # ######################## #
    # Clean start and end date #
    # ######################## #
    if start_date is None or end_date is None:
        return HttpResponseBadRequest("start and end date must be provided")

    # Start and end dates should be provided in ISO format
    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)
    except ValueError:
        return HttpResponseBadRequest("start and end date must be in yyyy-mm-ddThh:mm:ss+hh:mm format")

    # Start and end dates cannot differ more than a 'month' (7 days, 6 weeks)
    if (end_date - start_date).days > 42:
        return HttpResponseBadRequest("start and end date cannot differ more than 42 days")

    # ######################################################### #
    # Get all activity moments and convert them to JSON objects #
    # ######################################################### #

    activity_moment_jsons = []
    for activity in Activity.objects.filter(published_date__lte=timezone.now()):
        for activity_moment in activity.get_activitymoments_between(start_date, end_date):
            json_instance = get_json_from_activity_moment(activity_moment, user=request.user)
            activity_moment_jsons.append(json_instance)

    return JsonResponse({'activities': activity_moment_jsons})
