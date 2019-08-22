from django.shortcuts import render, get_object_or_404
from .models import Member, MemberLog
from .serializers import MemberSerializer
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe

# Renders the webpage for viewing all members
@require_safe
def viewAllMembers(request):
    serializer = MemberSerializer(Member.objects.all(), many=True)
    return render(request, 'membership_file/view-all-members.html', {"members": serializer.data})

# Renders the webpage for viewing a specific member
@require_safe
def viewSpecificMember(request, id):
    pMember = get_object_or_404(Member, pk=id)
    serializer = MemberSerializer(pMember)
    return render(request, 'membership_file/view-member.html', serializer.data)