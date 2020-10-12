from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_safe
from django.http import HttpResponseBadRequest

from .models import Activity


def check_join_constraints(request, parent_activity, recurrence_id):
    # Can only subscribe to at most X slots
    if parent_activity.max_slots_join_per_participant != -1 and \
            parent_activity.get_user_subscriptions(user=request.user, recurrence_id=recurrence_id).count() \
            >= parent_activity.max_slots_join_per_participant:
        return HttpResponseBadRequest("Cannot subscribe to another slot")


# The view that is accessed by FullCalendar to retrieve events
def get_activity_json(activity, start, end, user):
    activity_participants = activity.get_subscribed_participants(start)
    max_activity_participants = activity.get_max_num_participants(start)

    return {
        'groupId': activity.id,
        'title': activity.title,
        'description': activity.description,
        'location': activity.location,
        # use urlLink instead of url as that creates unwanted interactions with the calendar js module
        'urlLink': activity.get_absolute_url(recurrence_id=start),
        'recurrenceInfo': {
            'rrules': [rule.to_text() for rule in activity.recurrences.rrules],
            'exrules': [rule.to_text() for rule in activity.recurrences.exrules],
            'rdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity.recurrences.rdates],
            'exdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity.recurrences.exdates],
        },
        'subscriptionsRequired': activity.subscriptions_required,
        'numParticipants': activity_participants.count(),
        'maxParticipants': max_activity_participants,
        'isSubscribed': activity.is_user_subscribed(user, start,
                                                    participants=activity_participants),
        'canSubscribe': activity.can_user_subscribe(user, start,
                                                    participants=activity_participants, max_participants=max_activity_participants),
        'start': start.isoformat(),
        'end': end.isoformat(),
        'allDay': False,
    }

def get_json_from_activity_moment(activity_moment, user=None):
    return {
        'groupId': activity_moment.parent_activity.id,
        'title': activity_moment.title,
        'description': activity_moment.description,
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
        'numParticipants': activity_moment.get_subscribed_users().count(),
        'maxParticipants': activity_moment.max_participants,
        'isSubscribed': activity_moment.get_user_subscriptions(user).exists(),
        'canSubscribe': activity_moment.is_open_for_subscriptions(),
        'start': activity_moment.start_time.isoformat(),
        'end': activity_moment.end_time.isoformat(),
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
        for activity_moment in activity.get_all_activity_moments(start_date, end_date):
            json_instance = get_json_from_activity_moment(activity_moment, user=request.user)
            activity_moment_jsons.append(json_instance)

    return JsonResponse({'activities': activity_moment_jsons})
