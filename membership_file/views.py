from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView

# Redirect shortcuts
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe

from .models import MemberUser
from .models import Member, MemberLog
from .forms import MemberForm
from .util import membership_required, request_member, MembershipRequiredMixin

from core.views import TemplateManager

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *


# Add a link to each user's Account page leading to its Membership page
TemplateManager.set_template('core/user_accounts/account.html', 'membership_file/account_membership.html')


# Page that loads whenever a user tries to access a member-page
@require_safe
def viewNoMember(request):
    return render(request, 'membership_file/no_member.html', {})


# Page for viewing membership information
class MemberView(LoginRequiredMixin, MembershipRequiredMixin, DetailView):
    model = Member
    template_name = 'membership_file/view_member.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        # Odd loop-around because all logged in users should be treated as memberusers
        if self.request.user.is_authenticated:
            self.request.user.__class__ = MemberUser
            self.object = request.user.get_member()

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


# Renders the webpage for editing a user's own membership information
@membership_required
@request_member
def editOwnMembership(request):
    member = request.user.get_member()

    # Prevent access if the user is not authenticated, or if there was no membership
    # information linked to the user. I.e. the reuqest was forged!
    # Also deny access if the user is marked for deletion
    if request.user.is_anonymous or member is None or member.marked_for_deletion:
        #TODO: work with permission system so board members can edit other user's info with
        # the same form, without needing to be an admin (and doing it via the admin panel)
        return HttpResponseForbidden()

    # Process form data
    if request.method == 'POST':
        member.last_updated_by = request.user

        # Obtain the form that was entered
        form = MemberForm(request.POST, instance=member)

        # check whether the entered data was valid:
        if form.is_valid():
            # Save the updated info
            form.save(commit=True)      
            # Redirect back to the view membership info page
            # TODO: Provide a nice notification upon doing so
            return redirect(reverse('membership_file/membership'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MemberForm(instance=request.user.get_member())

    return render(request, 'membership_file/edit_member.html', {'form': form})
