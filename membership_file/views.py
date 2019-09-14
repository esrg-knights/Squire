from django.shortcuts import render, get_object_or_404
from .models import Member, MemberLog
from .serializers import MemberSerializer
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

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
    pMember = Member.objects.filter(user__id=request.user.id).first()
    serializer = MemberSerializer(pMember)
    return render(request, 'membership_file/view-member.html', serializer.data)


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
def editOwnMembership(request):
    pMember = Member.objects.filter(user__id=request.user.id).first()
    serializer = MemberSerializer(pMember)
    return render(request, 'membership_file/edit-member.html', serializer.data)
