from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Exists, OuterRef, Sum, Count
from django.http import (JsonResponse, HttpResponseBadRequest, HttpResponse,
        HttpResponseRedirect, HttpResponseNotFound, HttpResponseNotAllowed, HttpResponseForbidden)
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone, dateparse
from django.utils.http import urlencode
from django.utils.decorators import method_decorator
from django.contrib import messages

from django.views.decorators.http import require_safe, require_POST
from django.views.generic import DetailView
from django.views.generic.edit import FormView

from .forms import ActivitySlotForm, RegisterForSlotForm
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



def check_join_constraints(request, parent_activity, recurrence_id):
    # Can only subscribe to at most X slots
    if parent_activity.max_slots_join_per_participant != -1 and \
            parent_activity.get_user_subscriptions(user=request.user, recurrence_id=recurrence_id).count() \
                >= parent_activity.max_slots_join_per_participant:
        return HttpResponseBadRequest("Cannot subscribe to another slot")


@require_POST
@login_required
def deregister(request, slot_id):
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


class SlotMixin:
    slot = None
    def dispatch(self, request, *args, **kwargs):
        self.slot = get_object_or_404(ActivitySlot, id=kwargs['slot_id'])

        # Correct the class for the user
        self.request.user.__class__ = ExtendedUser

        return super(SlotMixin, self).dispatch(request, *args, **kwargs)


class RegisterToSlotView(SlotMixin, FormView):
    http_method_names = ['post']
    form_class = RegisterForSlotForm
    success_message = "You have successfully registered for {slot_name}"

    def get_form_kwargs(self):
        kwargs = super(RegisterToSlotView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'slot': self.slot,
        })
        print(self.request.user.__repr__())

        return kwargs

    def form_valid(self, form):
        form.save()

        if self.slot.parent_activity.slot_creation == "CREATION_AUTO":
            slot_name = self.slot.parent_activity.title
        else:
            slot_name = self.slot.title

        messages.success(self.request, self.success_message.format(slot_name=slot_name))
        return super(RegisterToSlotView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, form.get_error_message())

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.slot.get_absolute_url()





class ActivitySlotList(DetailView):

    model = Activity
    template_name = 'activity_calendar/activity_page_slots.html'
    context_object_name = 'activity'
    pk_url_kwarg = 'activity_id'

    def get(self, request, *args, **kwargs):
        # Obtain the relevant recurrence id
        self.object = self.get_object()
        self.recurrence_id = dateparse.parse_datetime(self.request.GET.get('date', ''))
        
        if self.recurrence_id is None or not self.object.has_occurence_at(self.recurrence_id):
            return HttpResponseNotFound()

        return super().get(request, args, kwargs)

    def get_template_names(self):
        if self.object.slot_creation == 'CREATION_AUTO':
            return 'activity_calendar/activity_page_single_signup.html'
        else:
            return self.template_name

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        recurrence_id = self.recurrence_id

        # Obtain information that is needed by the template
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
            if self.object.max_slots != -1:
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

        self.recurrence_id = dateparse.parse_datetime(request.GET.get('date', ''))
        if self.recurrence_id is None or not self.object.has_occurence_at(self.recurrence_id):
            return HttpResponseBadRequest()
        
        form.data._mutable = True
        form.data['parent_activity'] = self.object.id
        form.data['recurrence_id'] = self.recurrence_id
        form.data['owner'] = request.user.id

        if self.object.slot_creation == "CREATION_AUTO":
            form.data.update({
                'title':        'Slot ' + str(self.object.get_num_slots(recurrence_id=self.recurrence_id) + 1),
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
            request.user.__class__ = User
            slot.participants.add(request.user, through_defaults={})

            return redirect(request.get_full_path())
        else:
            context = context = self.get_context_data(**kwargs)
            context['form'] = form
            context['show_modal'] = True
            return self.render_to_response(context=context)
