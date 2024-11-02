from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, RequestFactory
from unittest.mock import MagicMock

from membership_file.exceptions import UserIsNotCurrentMember
from membership_file.middleware import MembershipMiddleware
from membership_file.models import Member


class MembershipMiddlewareTestCase(TestCase):
    fixtures = ["test_users", "test_members"]

    def setUp(self):
        get_response = MagicMock()
        self.middleware = MembershipMiddleware(get_response)

    def _create_request(self, user_id):
        request = RequestFactory().get("")
        request.user = User.objects.get(id=user_id)
        return request

    def test_process_request_not_a_member(self):
        request = self._create_request(2)
        self.middleware.process_request(request)
        self.assertEqual(request.member, None)

    def test_process_request_is_a_member(self):
        request = self._create_request(100)
        self.middleware.process_request(request)
        self.assertEqual(request.member, Member.objects.get(user__id=100))

    def test_process_request_anonymoususer(self):
        request = RequestFactory().get("")
        request.user = AnonymousUser()
        self.middleware.process_request(request)
        self.assertEqual(request.member, None)

    def test_process_exception(self):
        request = self._create_request(1)
        self.assertIsNone(
            self.middleware.process_exception(request, Exception())
        )  # Check if irrelevant errors are ignored

        response = self.middleware.process_exception(request, UserIsNotCurrentMember())
        self.assertIsNotNone(response)
        self.assertEqual(response.template_name, "membership_file/no_member.html")
        self.assertEqual(response.status_code, 403)
