from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone, dateparse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.decorators.http import require_safe
from django.views.generic import TemplateView
from django.views.generic.edit import FormView, FormMixin

from .forms import RegisterForActivityForm, RegisterForActivitySlotForm, RegisterNewSlotForm
from .models import Activity, Participant
from core.models import ExtendedUser


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


class LoginRequiredForPostMixin(AccessMixin):
    """ Requires being logged in for post events only (instead of the entire view) """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().post(request, *args, **kwargs)


class ActivityMixin:
    """ Mixin that retrieves the data for the current selected activity """

    def setup(self, request, *args, **kwargs):
        super(ActivityMixin, self).setup(request, *args, **kwargs)
        # Django calls the following line only in get(), which is too late
        self.activity = get_object_or_404(Activity, id=self.kwargs.get('activity_id'))
        self.recurrence_id = dateparse.parse_datetime(self.request.GET.get('date', ''))

        # Odd loop-around because all logged in users should be treated as extended users
        if self.request.user.is_authenticated:
            self.request.user.__class__ = ExtendedUser

        if self.recurrence_id is None or not self.activity.has_occurence_at(self.recurrence_id):
            raise Http404("We could not find the activity you are trying to reach")

    def get_context_data(self, **kwargs):
        kwargs = super(ActivityMixin, self).get_context_data(**kwargs)
        kwargs.update({
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
        })

        return kwargs


class ActivityMomentView(ActivityMixin, TemplateView):
    error_messages = {'undefined': _("Something went wrong. Please try again.")}

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        # Require logged in sessions
        if not request.user.is_authenticated:
            HttpResponseRedirect()

        form = self.get_form()
        if form.is_valid():
            try:
                output = form.save()
                if output:
                    message = "You have succesfully been added to {activity_name}"
                else:
                    message = "You have successfully been removed from {activity_name}"
                messages.success(self.request, message.format(activity_name=self.activity.title))
            except Exception:
                # This should theoretically not happen, but just in case there is a write error or something.
                messages.error(self.request, self.get_failed_message('undefined'))
        else:
            # Print a message with the reason why request could not be handled. It uses not the validation error
            # which is normally only form-phrased, but the error codes to get the proper user-phrased error message
            messages.error(self.request, self.get_failed_message(form.get_first_error_code()))

        # Do a redirect regardless of output. Form has no user input so is automatically up-to-date
        # Note: Do a redirect instead of render to prevent repeated sending when refreshing the page
        return HttpResponseRedirect(self.request.get_full_path())

    def get_failed_message(self, code):
        if code == 'undefined' or code is None:
            # Catch to prevent loops
            return self.error_messages.get(code, 'Undefined error occured')

        return self.error_messages.get(code, self.get_failed_message('undefined'))

    def get_context_data(self, **kwargs):
        kwargs = super(ActivityMomentView, self).get_context_data(**kwargs)
        kwargs.update({
            'subscriptions_open': self.activity.are_subscriptions_open(recurrence_id=self.recurrence_id),
            'num_total_participants': self.activity.get_num_subscribed_participants(recurrence_id=self.recurrence_id),
            'num_max_participants': self.activity.max_participants,
            'is_subscribed': self.activity.is_user_subscribed(self.request.user, self.recurrence_id),
            'start_date': self.recurrence_id,
            'end_date': self.recurrence_id + (self.activity.end_date - self.activity.start_date),
            'error_messages': self.error_messages,
        })

        return kwargs


class ActivitySimpleMomentView(LoginRequiredForPostMixin, FormMixin, ActivityMomentView):
    form_class = RegisterForActivityForm
    template_name = "activity_calendar/activity_page_no_slots.html"

    error_messages = {
        'undefined': _("Something went wrong. Please try again."),
        'activity-full': _("This activity is already at maximum capacity. You can not subscribe to it."),
        'invalid': _("You can not subscribe to this activity. Reason currently undefined"),
        'already-registered': _("You are already registered for this activity"),
        'not-registered': _("You are not registered to this activity"),
        'closed': _("You can not subscribe, subscriptions are currently closed"),
    }

    def get_form(self, form_class=None):
        # Intercept form creation for non-logged in users
        if self.request.user.is_authenticated:
            return super(ActivitySimpleMomentView, self).get_form(form_class=form_class)
        else:
            return None

    def get_form_kwargs(self):
        kwargs = {
            # Add some set-up data based on the current situation
            # This could be overwritten by the post data if supplied, which will yield the expected errors in that case
            'data': {
                'sign_up': not self.activity.is_user_subscribed(self.request.user, self.recurrence_id)
            },
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'user': self.request.user,
        }
        kwargs.update(super(ActivitySimpleMomentView, self).get_form_kwargs())
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(ActivitySimpleMomentView, self).get_context_data(**kwargs)
        kwargs.update({
            'participants': self.activity.get_subscribed_participants(recurrence_id=self.recurrence_id),
        })
        return kwargs


class ActivityMomentWithSlotsView(LoginRequiredForPostMixin, FormMixin, ActivityMomentView):
    form_class = RegisterForActivitySlotForm
    template_name = "activity_calendar/activity_page_slots.html"

    error_messages = {
        'undefined': _("Something went wrong. Please try again."),
        'activity-full': _("This activity is already at maximum capacity. You can not subscribe to it."),
        'invalid': _("You can not subscribe to this activity. Reason currently undefined"),
        'already-registered': _("You are already registered for this activity"),
        'not-registered': _("You are not registered to this activity"),
        'closed': _("You can not subscribe, subscriptions are currently closed"),
        'max-slots-occupied': _("You can not subscribe to another slot. Maximum number of subscribable slots already reached"),
    }

    def get_form_kwargs(self):
        kwargs = {
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'user': self.request.user,
        }
        kwargs.update(super(ActivityMomentWithSlotsView, self).get_form_kwargs())
        return kwargs

    def get_context_data(self, **kwargs):
        new_slot_form = RegisterNewSlotForm(
            initial={
                'sign_up': True,
            },
            activity=self.activity,
            user=self.request.user,
            recurrence_id=self.recurrence_id,
        )

        q_str = urlencode({'date': self.recurrence_id.isoformat()})
        register_link = f"{reverse('activity_calendar:create_slot', kwargs={'activity_id': self.activity.id})}?{q_str}"

        kwargs = super(ActivityMomentWithSlotsView, self).get_context_data(**kwargs)
        kwargs.update({
            'slot_list': self.activity.get_slots(self.recurrence_id),
            'subscribed_slots': self.activity.get_user_subscriptions(self.request.user, self.recurrence_id),
            'slot_creation_form': new_slot_form,
            'register_link': register_link,
        })
        return kwargs


def get_activity_detail_view(request, *args, **kwargs):
    """ Returns a HTTP response object by calling the required View Class """
    try:
        activity = Activity.objects.get(id=kwargs.get('activity_id', -1))
        if activity.slot_creation == "CREATION_AUTO":
            view_class = ActivitySimpleMomentView
        else:
            view_class = ActivityMomentWithSlotsView

        # Call the as_view() method as that method does more than just initialise a class
        return view_class.as_view()(request, *args, **kwargs)

    except Activity.DoesNotExist:
        # There is no activity with the given ID
        raise Http404("We could not find the activity you are trying to reach")


class CreateSlotView(LoginRequiredMixin, ActivityMixin, FormView):
    form_class = RegisterNewSlotForm
    template_name = "activity_calendar/new_slot_page.html"

    def get_form_kwargs(self):
        kwargs = super(CreateSlotView, self).get_form_kwargs()
        kwargs.update({
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):
        messages.info(request=self.request, message="form successfull")

        slot = form.save()
        return HttpResponseRedirect(slot.get_absolute_url())

