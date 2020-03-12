from django.shortcuts import render, get_object_or_404
from .models import MemberUser as User
from .models import Member, MemberLog
from .forms import MemberForm

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe
from .util import membership_required, request_member

# Redirect shortcuts
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

# Enable the auto-creation of logs
from .auto_model_update import *


# Page that loads whenever a user tries to access a member-page
@require_safe
def viewNoMember(request):
    return render(request, 'membership_file/no_member.html', {})


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
@request_member
def viewOwnMembership(request):
    tData = {'member': request.user.get_member()}
    return render(request, 'membership_file/view_member.html', tData)


# Renders the webpage for viewing a user's own membership information
@membership_required
@request_member
def editOwnMembership(request):
    # Process form data
    if request.method == 'POST':
        member = request.user.get_member()
        member.last_updated_by = request.user

        # Obtain the form that was entered
        form = MemberForm(request.POST, instance=member)

        # Prevent access if the user is not authenticated, or if there was no membership
        # information linked to the user. I.e. the reuqest was forged!
        if request.user.is_anonymous or member is None:
            #TODO: work with permission system so board members can edit other user's info with
            # the same form, without needing to be an admin (and doing it via the admin panel)
            return HttpResponseForbidden()

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
