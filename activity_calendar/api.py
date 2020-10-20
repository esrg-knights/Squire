from datetime import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_safe
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from django.views.decorators.http import require_POST

from .models import Activity, Participant, ActivitySlot
from core.models import ExtendedUser, PresetImage


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


@require_safe
def fullcalendar_feed(request):
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    # Start and end dates should be provided
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

    # Obtain non-recurring activities
    activities = []
    non_recurring_activities = (Activity.objects.filter(recurrences="", published_date__lte=timezone.now())
            # Activity starts between the specified bounds
        .filter((Q(start_date__gte=start_date, start_date__lte=end_date)
            # Activity ends between the specified bounds
            | Q(end_date__gte=start_date, end_date__lte=end_date)
            # Activity takes place between the specified bounds, but doesn't start/end in it
            | Q(start_date__lte=start_date, end_date__gte=end_date)))
    )

    for non_recurring_activity in non_recurring_activities:
        activities.append(get_activity_json(
            non_recurring_activity,
            non_recurring_activity.start_date,
            non_recurring_activity.end_date,
            request.user
        ))

    # Obtain occurrences of recurring activities in the relevant timeframe
    all_recurring_activities = Activity.objects.exclude(recurrences="").filter(published_date__lte=timezone.now())

    for recurring_activity in all_recurring_activities:
        recurrences = recurring_activity.recurrences
        event_start_time = recurring_activity.start_date.astimezone(timezone.get_current_timezone()).time()
        utc_start_time = recurring_activity.start_date.time()

        # recurrence expects each EXDATE's time to match the event's start time (in UTC; ignores DST)
        # Why it doesn't store it that way in the first place remains a mystery
        recurrences.exdates = list(map(lambda dt:
                                       datetime.combine(timezone.localtime(dt).date(),
                                                        utc_start_time, tzinfo=timezone.utc),
                                       recurrences.exdates
                                       ))

        # If the activity ends on a different day than it starts, this also needs to be the case for the occurrence
        time_diff = recurring_activity.end_date - recurring_activity.start_date

        for occurence in recurring_activity.get_occurences_between(start_date, end_date, inc=True):
            activities.append(get_activity_json(
                recurring_activity,
                occurence,
                (occurence + time_diff),
                request.user
            ))
    return JsonResponse({'activities': activities})
