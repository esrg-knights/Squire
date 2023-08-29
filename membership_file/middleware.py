from django.template.response import TemplateResponse
from django.utils.deprecation import MiddlewareMixin

from membership_file.exceptions import UserIsNotCurrentMember
from membership_file.models import Member


class MembershipMiddleware(MiddlewareMixin):
    """Middleware that adds the associated member to the the request class"""

    def process_request(self, request):
        assert hasattr(request, "user")
        if request.user.is_authenticated:
            request.member = Member.objects.filter(user__id=request.user.id).first()
        else:
            request.member = None

    def process_exception(self, request, exception):
        if isinstance(exception, UserIsNotCurrentMember):
            return TemplateResponse(
                request=request,
                template="membership_file/no_member.html",
                context={},
                status=403,
            )
