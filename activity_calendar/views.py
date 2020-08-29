from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Exists, OuterRef, Sum, Count
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone, dateparse
from django.utils.http import urlencode
from django.utils.decorators import method_decorator

from django.views.decorators.http import require_safe, require_POST
from django.views.generic import DetailView

from .forms import ActivitySlotForm
from .models import Activity, Participant, ActivitySlot
from core.models import ExtendedUser, PresetImage

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


def check_join_constraints(request, parent_activity, recurrence_id):
    # Can only subscribe to at most X slots
    if parent_activity.max_slots_join_per_participant >= 0 and \
            parent_activity.get_user_subscriptions(user=request.user, recurrence_id=recurrence_id).count() \
                >= parent_activity.max_slots_join_per_participant:
        return HttpResponseBadRequest("Cannot subscribe to another slot")

@require_POST
def register(request, slot_id):
    if request.user.is_anonymous:
        return HttpResponseBadRequest("Must be logged in to subscribe")

    slot = ActivitySlot.objects.filter(id=slot_id).first()
    parent_activity = slot.parent_activity
    if slot is None:
        return HttpResponseBadRequest(f"Expected the id of an existing ActivitySlot, but got <{slot_id}>")

    check_join_constraints(request, parent_activity, slot.recurrence_id)

    # Base check for general activity constraints: subscription period, max number of total participants, etc.
    if not slot.parent_activity.can_user_subscribe(request.user, recurrence_id=slot.recurrence_id):
        return HttpResponseBadRequest("Cannot subscribe")

    slot_participants = slot.participants.all()

    # Can only subscribe at most once to each slot
    if request.user in slot_participants:
        return HttpResponseBadRequest("Cannot subscribe to the same slot more than once")    

    # Slot participants limit
    if slot.max_participants >= 0 and len(slot_participants) >= slot.max_participants:
        return HttpResponseBadRequest("Slot is full")
    
    request.user.__class__ = ExtendedUser
    # Suscribe to slot
    participant = slot.participants.add(
       request.user, through_defaults={}
    )

    q_str = urlencode({'date': slot.recurrence_id.isoformat()})
    return HttpResponseRedirect(
        f"{reverse('activity_calendar:activity_slots_on_day', kwargs={'activity_id': parent_activity.id})}?{q_str}")

@require_POST
def deregister(request, slot_id):
    if request.user.is_anonymous:
        return HttpResponseBadRequest("Must be logged in to unsubscribe")

    slot = ActivitySlot.objects.filter(id=slot_id).first()
    parent_activity = slot.parent_activity
    if slot is None:
        return HttpResponseBadRequest(f"Expected the id of an existing ActivitySlot, but got <{slot_id}>")

    # Subscriptions must be open
    if not slot.are_subscriptions_open():
        return HttpResponseBadRequest(f"Cannot unsubscribe once subscriptions are closed")

    user_slot_participants = slot.participants.filter(id=request.user.id)

    for usr in user_slot_participants:
        slot.participants.remove(usr)

    q_str = urlencode({'date': slot.recurrence_id.isoformat(), 'deregister': True})
    return HttpResponseRedirect(
        f"{reverse('activity_calendar:activity_slots_on_day', kwargs={'activity_id': parent_activity.id})}?{q_str}")


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
        
        if recurrence_id is None:
            return HttpResponseNotFound()   

        slots = self.object.get_slots(recurrence_id=recurrence_id)
        num_total_participants = slots.aggregate(Count('participants'))['participants__count']
        num_max_participants = self.object.get_max_num_participants(recurrence_id=recurrence_id)

        context['deregister'] = self.request.GET.get('deregister', False)
        context['recurrence_id'] = recurrence_id
        context['slot_list'] = slots
        context['num_total_participants'] = num_total_participants
        context['max_participants'] = num_max_participants

        num_user_registrations = self.object.get_num_user_subscriptions(self.request.user, recurrence_id=recurrence_id)
        context['num_registered_slots'] = num_user_registrations
        context['can_create_slot'] = self.object.can_user_create_slot(self.request.user, recurrence_id=recurrence_id,
                num_slots=len(slots), num_user_registrations=num_user_registrations,
                num_total_participants=num_total_participants, num_max_participants=num_max_participants)
        context['subscriptions_open'] = self.object.are_subscriptions_open(recurrence_id=recurrence_id)
        
        
        duration = self.object.end_date - self.object.start_date
        self.object.start_date = recurrence_id
        self.object.end_date = self.object.start_date + duration

        context['num_dummy_slots'] = 0

        if self.object.slot_creation == "CREATION_USER":
            context['form'] = ActivitySlotForm(instance=None)
        elif self.object.slot_creation == "CREATION_AUTO":
            context['num_dummy_slots'] = self.object.MAX_NUM_AUTO_DUMMY_SLOTS
            if self.object.max_slots >= 0:
                context['num_dummy_slots'] = max(0, min(self.object.MAX_NUM_AUTO_DUMMY_SLOTS, self.object.max_slots - len(slots)))

        # The object is already passed as 'activity'; no need to send it over twice
        del context['object']
        return context
    
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.slot_creation == "CREATION_NONE":
            return HttpResponseNotAllowed(['GET'])

        form = ActivitySlotForm(request.POST)

        recurrence_id = dateparse.parse_datetime(request.GET.get('date'))
        if recurrence_id is None:
            return HttpResponseBadRequest()   
        
        form.data._mutable = True
        form.data['parent_activity'] = self.object.id
        form.data['recurrence_id'] = recurrence_id
        form.data['owner'] = request.user.id

        if self.object.slot_creation == "CREATION_AUTO":
            form.data.update({
                'title':        'Slot ' + str(self.object.get_num_slots(recurrence_id=recurrence_id) + 1),
                'description':  None,
                'location':     None,
                'start_date':   None,
                'end_date':     None,
                'max_participants': -1,
                'owner':        None,
                'image':        None,
            })        

        if form.is_valid():
            # Save the slot and add the user
            slot = form.save(commit=True)
            request.user.__class__ = ExtendedUser
            slot.participants.add(request.user, through_defaults={})

            return redirect(request.get_full_path())
        else:
            context = context = self.get_context_data(**kwargs)
            context['form'] = form
            context['show_modal'] = True
            return self.render_to_response(context=context)
