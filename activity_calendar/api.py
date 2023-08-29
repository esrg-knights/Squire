from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_safe
from django.http import HttpResponseBadRequest

from .models import Activity
from .constants import ActivityType


def get_json_from_activity_moment(activity_moment, user=None):
    return {
        "groupId": activity_moment.parent_activity.id,
        "title": activity_moment.title,
        "description": activity_moment.description.as_rendered(),
        "location": activity_moment.location,
        # use urlLink instead of url as that creates unwanted interactions with the calendar js module
        "urlLink": activity_moment.get_absolute_url(),
        "recurrenceInfo": {
            "rrules": [rule.to_text() for rule in activity_moment.parent_activity.recurrences.rrules],
            "exrules": [rule.to_text() for rule in activity_moment.parent_activity.recurrences.exrules],
            "rdates": [
                occ.date().strftime("%A, %B %d, %Y") for occ in activity_moment.parent_activity.recurrences.rdates
            ],
            "exdates": [
                occ.date().strftime("%A, %B %d, %Y") for occ in activity_moment.parent_activity.recurrences.exdates
            ],
        },
        "subscriptionsRequired": activity_moment.subscriptions_required,
        "numParticipants": activity_moment.participant_count,
        "maxParticipants": activity_moment.max_participants,
        "isSubscribed": activity_moment.get_user_subscriptions(user).exists(),
        "canSubscribe": activity_moment.is_open_for_subscriptions(),
        "start": activity_moment.start_date.isoformat(),
        "recurrence_id": activity_moment.recurrence_id.isoformat(),
        "end": activity_moment.end_date.isoformat(),
        "allDay": False,
        "is_cancelled": activity_moment.is_cancelled,
    }


@require_safe
def fullcalendar_feed(request):
    """
    Get a collection of activity occurrences between a specified start and end time.
    Used by the FullCalendar library.
    """
    start_date = request.GET.get("start", None)
    end_date = request.GET.get("end", None)

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
    for activity in Activity.objects.filter(published_date__lte=timezone.now(), type=ActivityType.ACTIVITY_PUBLIC):
        for activity_moment in activity.get_activitymoments_between(start_date, end_date):
            json_instance = get_json_from_activity_moment(activity_moment, user=request.user)
            activity_moment_jsons.append(json_instance)

    return JsonResponse({"activities": activity_moment_jsons})


@require_safe
def upcoming_core_feed(request):
    """
    A collection of the first occurrence of all core activities. E.g. the first
    upcoming boardgame-related activity, the first upcoming swordfighting training, etc.
    Skips cancelled and removed activities.
    Used on kotkt.nl
    """
    grouping_identifiers = request.GET.get("groups", "").split(",")

    now = timezone.now()

    # Add placeholders to ensure the order of the groupings does not change
    earliest_moments = {x: None for x in grouping_identifiers}

    # Iterate over all published activities that are part of the core groupings in the GET request
    for activity in Activity.objects.select_related("core_grouping").filter(
        published_date__lte=now, core_grouping__identifier__in=grouping_identifiers
    ):
        # Fetch the next activitymoment (if any) for this activity that is not cancelled
        activity_moment = activity.get_next_activitymoment(dtstart=now, exclude_cancelled=True, exclude_removed=True)
        earliest_moment = earliest_moments.get(activity.core_grouping.identifier, None)
        # Does this activity take place earlier than the current earliest activitymoment for this grouping?
        if earliest_moment is None or earliest_moment.start_date > activity_moment.start_date:
            earliest_moments[activity.core_grouping.identifier] = activity_moment

    # Fetch data for the selected activitymoments
    activity_moment_jsons = []
    for identifier, activity_moment in earliest_moments.items():
        if activity_moment is None:
            # Silently fail if no activitymoment for the identifier was found.
            #   This can happen if all remaining occurrences are cancelled/removed,
            #   if there are no activities with the given identifier,
            #   or if the given identifier does not even exist.
            # We're not explicitly failing because there might still be other (valid) activitymoments
            #   for other identifiers that were also passed in the same request.
            continue

        activity_moment_jsons.append(
            {
                "title": activity_moment.title,
                "description": activity_moment.description.as_rendered(),
                "location": activity_moment.location,
                "urlLink": activity_moment.get_absolute_url(),
                "subscriptionsRequired": activity_moment.subscriptions_required,
                "numParticipants": activity_moment.participant_count,
                "maxParticipants": activity_moment.max_participants,
                "canSubscribe": activity_moment.is_open_for_subscriptions(),
                "start": activity_moment.start_date.isoformat(),
                "end": activity_moment.end_date.isoformat(),
                "allDay": False,
                "is_cancelled": activity_moment.is_cancelled,
                "core_grouping_identifier": identifier,
            }
        )
    return JsonResponse({"activities": activity_moment_jsons})
