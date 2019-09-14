from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from .models import Member, MemberLog

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
    tData = {'member': Member.objects.filter(user__id=request.user.id).first()}
    return render(request, 'membership_file/view_member.html', tData)


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
def editOwnMembership(request):
    tData = {'member': Member.objects.filter(user__id=request.user.id).first()}
    return render(request, 'membership_file/edit_member.html', tData)
