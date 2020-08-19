from datetime import datetime

from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe

from .models import Activity

# Renders the simple v1 calendar
@require_safe
def googlehtml_activity_collection(request):
    return render(request, 'activity_calendar/calendar.html', {})

# Renders the calendar page, which utilises FullCalendar
@require_safe
def activity_collection(request):
    return render(request, 'activity_calendar/fullcalendar.html', {})

# The view that is accessed by FullCalendar to retrieve events
def get_activity_json(activity, start, end):
    return {
        'groupId': activity.id,
        'title': activity.title,
        'description': activity.description,
        'location': activity.location,
        'recurrenceInfo': {
            'rrules': [rule.to_text() for rule in activity.recurrences.rrules],
            'exrules': [rule.to_text() for rule in activity.recurrences.exrules],
            'rdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity.recurrences.rdates],
            'exdates': [occ.date().strftime("%A, %B %d, %Y") for occ in activity.recurrences.exdates],
        },
        'start': start,
        'end': end,
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
    non_recurring_activities = Activity.objects.filter(recurrences="", published_date__lte=timezone.now()) \
            .filter((Q(start_date__gte=start_date) | Q(end_date__lte=end_date)))
    
    for non_recurring_activity in non_recurring_activities:
        activities.append(get_activity_json(
            non_recurring_activity,
            non_recurring_activity.start_date.isoformat(),
            non_recurring_activity.end_date.isoformat()
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

        for occurence in recurrences.between(start_date, end_date, dtstart=recurring_activity.start_date, inc=True):
            # recurrence does not handle daylight-saving time! If we were to keep the occurence as is,
            # then summer events would occur an hour earlier in winter!
            occurence = timezone.get_current_timezone().localize(
                datetime.combine(timezone.localtime(occurence).date(), event_start_time)
            )

            activities.append(get_activity_json(
                recurring_activity,
                occurence.isoformat(),
                (occurence + time_diff).isoformat(),
            ))

    return JsonResponse({'activities': activities})
