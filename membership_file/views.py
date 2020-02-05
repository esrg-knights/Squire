from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from .models import Member, MemberLog
from .forms import MemberForm

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe
from core.util import membership_required

# Enable the auto-creation of logs
from .auto_model_update import *


# Page that loads whenever
@require_safe
def viewNoMember(request):
    return render(request, 'membership_file/no_member.html', {})


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
def viewOwnMembership(request):
    tData = {'member': request.user.get_member()}
    return render(request, 'membership_file/view_member.html', tData)


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
def editOwnMembership(request):
    # Process form data
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=request.user.get_member())
        # check whether it's valid:
        if form.is_valid():
            # Save the user
            form.save(commit=True)            
            return redirect(reverse('core/user_accounts/register/success')) #TODO

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MemberForm(instance=request.user.get_member())

    return render(request, 'membership_file/edit_member.html', {'form': form})
