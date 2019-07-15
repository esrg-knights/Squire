from django.shortcuts import render, get_object_or_404
from .models import Member, MemberLog
from .serializers import MemberSerializer
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe

# Enable the auto-creation of logs
from .auto_model_update import *


# API calls made to /members/
class MemberView(APIView):
    def get(self, request, format=None):
        #Convert model instance to a dictionary
        serializer = MemberSerializer(Member.objects.all(), many=True)
        return Response({"members": serializer.data})
    def post(self, request, format=None):
        pass


# API calls made to /members/<int:id>/
class SpecificMemberView(APIView):
    def get(self, request, id, format=None):
        pMember = get_object_or_404(Member, pk=id)
        #Convert model instance to a dictionary
        serializer = MemberSerializer(pMember)

        return Response(serializer.data)
    def put(self, request, id, format=None):
        pass
    
    def delete(self, request, id, format=None):
        pass
