from django.utils.deprecation import MiddlewareMixin

from membership_file.models import Member



class MembershipMiddleware(MiddlewareMixin):
    """ Middleware that adds the associated member to the the request class """

    def process_request(self, request):
        assert hasattr(request, 'user')
        if request.user.is_authenticated:
            request.member = Member.objects.filter(user__id=request.user.id).first()
        else:
            request.member = None
