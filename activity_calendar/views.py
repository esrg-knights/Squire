from datetime import datetime, timedelta

from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from django.views.decorators.http import require_safe
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, FormMixin

from .forms import *
from .models import Activity, ActivityMoment
from core.models import ExtendedUser

__all__ = "CreateSlotView, get_activity_detail_view, activity_collection"


# Renders the calendar page, which utilises FullCalendar
@require_safe
def activity_collection(request):
    return render(request, 'activity_calendar/fullcalendar.html', {})


class ActivityOverview(ListView):
    template_name = "activity_calendar/activity_overview.html"
    context_object_name = 'activities'

    def get_queryset(self):
        start_date = timezone.now()
        end_date = start_date + timedelta(days=14)

        activities = []

        for activity in Activity.objects.filter(published_date__lte=timezone.now()):
            for activity_moment in activity.get_activitymoments_between(start_date, end_date):
                activities.append(activity_moment)

        return sorted(activities, key=lambda activity: activity.start_date)


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
        self.recurrence_id = self.kwargs.get('recurrence_id', None)

        self.activity_moment = ActivityMoment.objects.filter(
            parent_activity=self.activity,
            recurrence_id=self.recurrence_id
        ).first()

        if self.activity_moment is None:
            if not self.activity.has_occurrence_at(self.recurrence_id):
                raise Http404("We could not find the activity you are trying to reach")
            else:
                self.activity_moment = ActivityMoment(
                    parent_activity=self.activity,
                    recurrence_id=self.recurrence_id,
                )

        # Odd loop-around because all logged in users should be treated as extended users
        if self.request.user.is_authenticated:
            self.request.user.__class__ = ExtendedUser

    def get_context_data(self, **kwargs):
        kwargs = super(ActivityMixin, self).get_context_data(**kwargs)
        kwargs.update({
            'activity': self.activity,
            'activity_moment': self.activity_moment,
            'recurrence_id': self.recurrence_id,
            # General information displayed on all relevant pages
            'subscriptions_open': self.activity_moment.is_open_for_subscriptions(),
            'num_total_participants': self.activity_moment.participant_count,
            'num_max_participants': self.activity_moment.max_participants,
            'user_subscriptions': self.activity_moment.get_user_subscriptions(self.request.user),
            'show_participants': self.show_participants(),
        })

        return kwargs

    def show_participants(self):
        """ Returns whether to show participant names """
        now = timezone.now()

        if now < self.activity_moment.start_date:
            return self.request.user.has_perm('activity_calendar.can_view_activity_participants_before')
        elif now > self.activity_moment.end_date:
            return self.request.user.has_perm('activity_calendar.can_view_activity_participants_after')
        return self.request.user.has_perm('activity_calendar.can_view_activity_participants_during')


class ActivityFormMixin:
    error_messages = {'undefined': _("Something went wrong. Please try again.")}

    def get_success_message(self, form):
        """ Returns the message that will be displayed to the user after form success """
        if form.cleaned_data['sign_up']:
            message = _("You have succesfully been added to '{activity_name}'")
        else:
            message = _("You have successfully been removed from '{activity_name}'")

        return message

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        if form.is_valid():
            try:
                form.save()
            except Exception:
                # This should theoretically not happen, but just in case there is a write error or something.
                messages.error(self.request, self.get_failed_message('undefined'))
            else:
                messages.success(self.request, self.get_success_message(form))
        else:
            # Print a message with the reason why request could not be handled. It uses not the validation error
            # which is normally only form-phrased, but the error codes to get the proper user-phrased error message
            messages.error(self.request, self.get_failed_message(form.get_first_error_code()))

        # Do a redirect regardless of output. Form has no user input so is automatically up-to-date
        # Note: Do a redirect instead of render to prevent repeated sending when refreshing the page
        return HttpResponseRedirect(self.request.get_full_path())

    @classmethod
    def get_failed_message(cls, code):
        if code == 'undefined' or code is None:
            # Catch to prevent loops
            return cls.error_messages.get(code, 'Undefined error occured')

        return cls.error_messages.get(code, cls.get_failed_message('undefined'))

    def get_context_data(self, **kwargs):
        kwargs = super(ActivityFormMixin, self).get_context_data(**kwargs)
        kwargs.update({
            'error_messages': self.error_messages,
        })

        return kwargs


class ActivityMomentView(ActivityMixin, ActivityFormMixin, TemplateView):
    pass


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
                'sign_up': not self.activity_moment.get_user_subscriptions(self.request.user).exists(),
            },
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'activity_moment': self.activity_moment,
            'user': self.request.user,
        }
        kwargs.update(super(ActivitySimpleMomentView, self).get_form_kwargs())
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(ActivitySimpleMomentView, self).get_context_data(**kwargs)
        kwargs.update({
            'subscribed_users': self.activity_moment.get_subscribed_users(),
            'subscribed_guests': self.activity_moment.get_guest_subscriptions()
        })
        return kwargs

    def get_success_message(self, form):
        return super(ActivitySimpleMomentView, self).get_success_message(form).format(
            activity_name=self.activity_moment.title
        )


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
        'slot-full': _("You can not join this slot. It's already at maximum capacity"),
        'max-slots-occupied': _(
            "You can not subscribe to another slot. Maximum number of subscribable slots already reached"),
        # Slot creation error messages
        'max-slots-claimed': _(
            "You can not create a slot because this activity already has the maximum number of allowed slots"),
        'user-slot-creation-denied': _(
            "You can not create slots on this activity. I honestly don't know why I'm even showing you this option.")
    }

    def get_success_message(self, form):
        msg = super(ActivityMomentWithSlotsView, self).get_success_message(form)
        if form.slot_obj:
            return msg.format(
                activity_name=form.slot_obj.title
            )
        else:
            raise KeyError("Form cleaned data did not contain slot_obj. How can this form be valid?")

    def get_form_kwargs(self):
        kwargs = {
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'activity_moment': self.activity_moment,
            'user': self.request.user,
        }
        kwargs.update(super(ActivityMomentWithSlotsView, self).get_form_kwargs())
        return kwargs

    def get_context_data(self, **kwargs):
        # Determine if the mode allows slot creation. If mode is None, staff users should be able to create slots
        # Note that actual validation always takes place in the form itself, this is merely whether, without any actual
        # input on the complex database status (i.e. relations), this button needs to be shown.
        if self.activity_moment.slot_creation == Activity.SLOT_CREATION_USER:
            new_slot_form = RegisterNewSlotForm(
                initial={
                    'sign_up': True,
                },
                activity=self.activity,
                user=self.request.user,
                recurrence_id=self.recurrence_id,
                activity_moment=self.activity_moment,
            )
        elif self.activity_moment.slot_creation == Activity.SLOT_CREATION_STAFF and \
                self.request.user.has_perm('activity_calendar.can_ignore_none_slot_creation_type'):
            # In a none based slot mode, don't automatically register the creator to the slot
            new_slot_form = RegisterNewSlotForm(
                initial={
                    'sign_up': False,
                },
                activity=self.activity,
                user=self.request.user,
                recurrence_id=self.recurrence_id,
                activity_moment=self.activity_moment,
            )
        else:
            new_slot_form = None

        register_link = reverse('activity_calendar:create_slot', kwargs={
            'activity_id': self.activity.id,
            'recurrence_id': self.recurrence_id
        })

        kwargs = super(ActivityMomentWithSlotsView, self).get_context_data(**kwargs)
        kwargs.update({
            'slot_list': self.activity_moment.get_slots(),
            'slot_creation_form': new_slot_form,
            'register_link': register_link,
        })
        return kwargs


def get_activity_detail_view(request, *args, **kwargs):
    """ Returns a HTTP response object by calling the required View Class """
    try:
        recurrence_id = kwargs.get('recurrence_id', None)
        if recurrence_id is None:
            raise Http404("The timestamp was not correctly written")

        activity = Activity.objects.get(id=kwargs.get('activity_id', -1))

        activity_moment = ActivityMoment.objects.filter(
            parent_activity=activity,
            recurrence_id=recurrence_id
        ).first()

        if activity_moment is None:
            activity_moment = activity

        if activity_moment.slot_creation == Activity.SLOT_CREATION_AUTO:
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
    template_name = "activity_calendar/activity_page_new_slot.html"

    error_messages = {
        'undefined': _("Something went wrong. Please try again."),
        'activity-full': _("This activity is already at maximum capacity. You can not subscribe to it."),
        'invalid': _("You can not subscribe to this activity. Reason currently undefined"),
        'closed': _("You can not create slots as subscriptions are currently closed"),
        'max-slots-occupied': _(
            "You can not create and subscribe to another slot. You are already at your maximum number of slots you can register for"),
        'max-slots-claimed': _(
            "You can not create a slot because this activity already has the maximum number of allowed slots"),
        'user-slot-creation-denied': _("You can not create slots on this activity.")
    }

    def render_to_response(self, context, **response_kwargs):
        # Interject the resposne method. If the form has base errors, instead of rendering. Default to the normal
        # activity page and display the error message. As it is a base error the user can not view the slot creation
        # page anyway
        error = context['form'].get_base_validity_error()
        if error:
            messages.error(self.request, self.error_messages.get(error.code, 'An unknown error occured'))
            return HttpResponseRedirect(self.activity.get_absolute_url(self.recurrence_id))

        return super(CreateSlotView, self).render_to_response(context, **response_kwargs)

    def get_form_kwargs(self):
        if self.activity_moment.slot_creation == Activity.SLOT_CREATION_STAFF:
            # In a none based slot mode, don't automatically register the creator to the slot
            initial = {'sign_up': False}
        else:
            initial = {'sign_up': True}

        kwargs = super(CreateSlotView, self).get_form_kwargs()
        kwargs.update({
            'initial': initial,
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'activity_moment': self.activity_moment,
            'user': self.request.user,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        return super(CreateSlotView, self).get_context_data(**{
            'subscribed_slots': self.activity_moment.get_user_subscriptions(self.request.user),
        })

    def form_valid(self, form):
        slot = form.save()
        if form.cleaned_data['sign_up']:
            message = _("You have successfully created and joined '{activity_name}'")
        else:
            message = _("You have successfully created '{activity_name}'")
        messages.success(self.request, message.format(activity_name=form.instance.title))

        return HttpResponseRedirect(slot.get_absolute_url())

    def form_invalid(self, form):
        error = form.get_base_validity_error()
        # If any of the base errors occured, the user can not prevent or address the problem to fix it in the form
        # Thus return it to the normal page instead of displaying the page again.
        if error:
            messages.error(self.request, self.error_messages.get(error.code, 'An unknown error occured'))
            return HttpResponseRedirect(self.activity.get_absolute_url(self.recurrence_id))
        else:
            messages.error(self.request, _("Some input was not valid. Please correct your data below"))
            return super(CreateSlotView, self).form_invalid(form)


# #######################################
# ######   Activity Editing View   ######
# #######################################


class EditActivityMomentView(LoginRequiredMixin, PermissionRequiredMixin, ActivityMixin, FormView):
    form_class = ActivityMomentForm
    template_name = "activity_calendar/activity_moment_form_page.html"
    permission_required = ('activity_calendar.change_activitymoment',)

    def get_form_kwargs(self):
        kwargs = super(EditActivityMomentView, self).get_form_kwargs()
        kwargs.update({
            'instance': self.activity_moment,
            'user': self.request.user, # Needed for MarkdownImage uploads
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        message = _("You have successfully changed the settings for '{activity_name}'")
        messages.success(self.request, message.format(activity_name=form.instance.title))
        return super(EditActivityMomentView, self).form_valid(form)

    def get_success_url(self):
        return self.activity_moment.get_absolute_url()
