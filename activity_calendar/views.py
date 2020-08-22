from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils import timezone, dateparse
from django.views.decorators.http import require_safe
from django.views.generic import DetailView

from .models import Activity

# Renders the simple v1 calendar
@require_safe
def googlehtml_activity_collection(request):
    return render(request, 'activity_calendar/googlecalendar.html', {})

# Renders the calendar page, which utilises FullCalendar
@require_safe
def activity_collection(request):
    return render(request, 'activity_calendar/fullcalendar.html', {})

# The view that is accessed by FullCalendar to retrieve events
def get_activity_json(activity, start, end, user):
    activity_participants = activity.get_subscribed_participants(start)
    max_activity_participants = activity.get_max_num_participants(start)

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
    non_recurring_activities = Activity.objects.filter(recurrences="", published_date__lte=timezone.now()) \
            .filter((Q(start_date__gte=start_date) | Q(end_date__lte=end_date)))
    
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

        for occurence in recurrences.between(start_date, end_date, dtstart=recurring_activity.start_date, inc=True):
            # recurrence does not handle daylight-saving time! If we were to keep the occurence as is,
            # then summer events would occur an hour earlier in winter!
            occurence = timezone.get_current_timezone().localize(
                datetime.combine(timezone.localtime(occurence).date(), event_start_time)
            )
            
            activities.append(get_activity_json(
                recurring_activity,
                occurence,
                (occurence + time_diff),
                request.user
            ))

    return JsonResponse({'activities': activities})

# Shows the slots for some activity on some date
@require_safe
@login_required
def show_activity_slots_on_date(request, activity_id, year, month, day):
    activity = Activity.objects.get(id=activity_id)
    print(activity)


class ActivitySlotList(DetailView):

    model = Activity
    template_name = 'activity_calendar/activity_slots.html'
    context_object_name = 'activity'
    pk_url_kwarg = 'activity_id'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Add the activity's slots as well as some general info
        recurrence_id = dateparse.parse_datetime(self.request.GET.get('date'))
        context['recurrence_id'] = recurrence_id
        context['slot_list'] = self.object.get_slots(recurrence_id=recurrence_id)
        context['subscriptions_open'] = self.object.are_subscriptions_open(recurrence_id=recurrence_id)
        context['num_registered_slots'] = self.object.get_num_user_subscriptions(self.request.user, recurrence_id=recurrence_id)
        del context['object']
        # print(context['slot_list'].first().image)
        print(context)
        return context
