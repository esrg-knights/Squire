from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_safe

from .models import MemberUser as User
from .models import Member, MemberLog
from .forms import MemberForm
from .util import membership_required, request_member

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


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
@permission_required('membership_file.can_view_membership_information_self', raise_exception=True)
@request_member
def viewOwnMembership(request):
    tData = {'member': request.user.get_member()}
    return render(request, 'membership_file/view_member.html', tData)


# Renders the webpage for editing a user's own membership information
@membership_required
@permission_required('membership_file.can_view_membership_information_self', raise_exception=True)
@permission_required('membership_file.can_change_membership_information_self', raise_exception=True)
@request_member
def editOwnMembership(request):
    member = request.user.get_member()

    # Members who are marked for deletion cannot be edited
    if member.marked_for_deletion:
        #TODO: work with permission system so board members can edit other user's info with
        # the same form, without needing to be an admin (and doing it via the admin panel)
        raise PermissionDenied

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
