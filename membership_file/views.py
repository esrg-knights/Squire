from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from dynamic_preferences.registries import global_preferences_registry

from .util import MembershipRequiredMixin

# Enable the auto-creation of logs
from membership_file.forms import ContinueMembershipForm

global_preferences = global_preferences_registry.manager()


class MemberMixin(MembershipRequiredMixin):
    """
        Sets the view's object to the Member corresponding to the user that makes
        the request.
    """
    def get_object(self, queryset=None):
        return self.request.member


# Page that loads whenever a user tries to access a member-page
class NotAMemberView(TemplateView):
    template_name = 'membership_file/no_member.html'


class ExtendMembershipView(FormView):
    template_name = "membership_file/extend_membership.html"
    form_class = ContinueMembershipForm
    success_url = reverse_lazy('membership_file/continue_success')

    def get_form_kwargs(self):
        kwargs = super(ExtendMembershipView, self).get_form_kwargs()
        kwargs.update({
            'member': self.request.member,
            'year': global_preferences['membership__signup_year']
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(ExtendMembershipView, self).form_valid(form)


class ExtendMembershipSuccessView(TemplateView):
    template_name = "membership_file/extend_membership_successpage.html"
