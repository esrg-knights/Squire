from django.shortcuts import render, get_object_or_404
from .models import Member, MemberLog
from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView, Response

# Renders the webpage for viewing all members
def viewAllMembers(request):
    serializer = MemberSerializer(Member.objects.all(), many=True)
    return render(request, 'membership_file/view-all-members.html', {"members": serializer.data})

# Renders the webpage for viewing a specific member
def viewSpecificMember(request, id):
    print(id)
    pMember = get_object_or_404(Member, pk=id)
    serializer = MemberSerializer(pMember)
    return render(request, 'membership_file/view-member.html', serializer.data)



# The MemberSerializer converts the Member model to a Python dictionary
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"
        depth = 1

# API calls made to /members/
class MemberView(APIView):
    def get(self, request, format=None):
        #Convert model instance to a dictionary
        serializer = MemberSerializer(Member.objects.all(), many=True)
        return Response({"members": serializer.data})
    def put(self, request, format=None):
        pass
    def post(self, request, format=None):
        pass


# API calls made to /members/<int:id>/
class SpecificMemberView(APIView):
    def get(self, request, id, format=None):
        pMember = get_object_or_404(Member, pk=id)
        #Convert model instance to a dictionary
        serializer = MemberSerializer(pMember)

        return Response(serializer.data)

    def post(self, request, id, format=None):
        pass

    def put(self, request, id, format=None):
        pass
    
    def delete(self, request, id, format=None):
        pass
