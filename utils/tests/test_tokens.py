from typing import Optional, Tuple
from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase
from django.template.response import TemplateResponse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import TemplateView

from utils.tokens import SessionTokenMixin, UrlTokenMixin

UserModel = get_user_model()


class SessionTokenViewMixinTestCase(TestCase):
    """Tests access requirements for views that fetch a token from the session data, partially like Django's `PasswordResetConfirmView`"""

    class DummySessionView(SessionTokenMixin, TemplateView):
        """Simple view that mimics Django's password reset token generation"""

        template_name = "utils/testing/test_mixin_template.html"
        fail_template_name = "utils/testing/token_fail_template.html"
        session_token_name = "_my_session_token"
        token_generator = PasswordResetTokenGenerator()

    view_class = DummySessionView

    def setUp(self) -> None:
        self.view = self.view_class.as_view()
        self.request_factory = RequestFactory()
        get_response = MagicMock()
        self.middleware = SessionMiddleware(get_response)

        self.user = UserModel.objects.create(username="user")

        return super().setUp()

    def build_response(
        self, token_user: UserModel, request_user: Optional[UserModel] = None, token: Optional[str] = None
    ) -> Tuple[HttpRequest, TemplateResponse]:
        """
        Builds a request made by `request_user`, with url kwargs for a base64 encoded `token_user` and a `token`.
        If `token` is omitted, a valid token is generated based on the `token_user`
        """
        token = token or self.view_class.token_generator.make_token(token_user)
        uidb64 = urlsafe_base64_encode(force_bytes(token_user.pk))
        req: HttpRequest = self.request_factory.get(f"/my_path/{token}/foo/{uidb64}/bar/")
        req.user = request_user

        # Enable session middleware
        self.middleware.process_request(req)
        req.session.save()

        return req, uidb64, token

    def test_token_session_success(self):
        """Tests token handling with valid session tokens"""
        req, uidb64, token = self.build_response(self.user)
        req.session[self.view_class.session_token_name] = token
        res = self.view(req, uidb64=uidb64)
        self.assertEqual(res.status_code, 200)
        # TemplateView converts template_name into a list
        self.assertListEqual(
            res.template_name,
            [self.view_class.template_name],
            "Success template should be used when token is valid.",
        )

    def _test_token_fail(self, request: HttpRequest, response: TemplateResponse, msg: str = "Token"):
        """Common checks for failed tokens"""
        self.assertEqual(response.status_code, 400, f"{msg} is invalid; should stay on page")
        self.assertEqual(
            response.template_name,
            self.view_class.fail_template_name,
            "Fail template should be used when token is invalid.",
        )
        self.assertNotIn(
            self.view_class.session_token_name,
            request.session,
            "Session token should not be set when token is invalid",
        )

    def test_token_url_fail(self):
        """Tests token handling with invalid tokens in the URL"""
        # Token already replaced in URL, but not present in session data
        req, uidb64, token = self.build_response(self.user)
        res = self.view(req, uidb64=uidb64)
        self._test_token_fail(req, res)

    def test_token_session_fail(self):
        """Tests token handling with invalid tokens in the session"""
        # Invalid token present in session data
        req, uidb64, token = self.build_response(self.user)
        req.session[self.view_class.session_token_name] = "INVALID"
        res = self.view(req, uidb64=uidb64)
        self.assertEqual(res.status_code, 400, f"Token in session is invalid; should stay on page")

        self.assertEqual(
            res.template_name,
            self.view_class.fail_template_name,
            "Fail template should be used when token is invalid.",
        )

    def test_user_fail(self):
        """Tests token handling if the user in the url is invalid"""
        # Base64 text is invalid
        req, _, token = self.build_response(self.user)
        res = self.view(req, uidb64="1")
        self._test_token_fail(req, res, msg="base64 encoded user")

        # User does not exist
        req, _, token = self.build_response(self.user)
        res = self.view(req, uidb64=urlsafe_base64_encode(force_bytes(42)))
        self._test_token_fail(req, res, msg="Non-existing user")


class UrlTokenViewMixinTestCase(TestCase):
    """Tests access requirements for views that fetch and set a token through a URL, like Django's `PasswordResetConfirmView`"""

    class DummyUrlView(UrlTokenMixin, TemplateView):
        """Simple view that mimics Django's password reset token generation"""

        template_name = "utils/testing/test_mixin_template.html"
        fail_template_name = "utils/testing/token_fail_template.html"
        session_token_name = "_my_session_token"
        token_generator = PasswordResetTokenGenerator()
        url_token_name = "token-replacement-in-url"

    view_class = DummyUrlView

    def setUp(self) -> None:
        self.view = self.view_class.as_view()
        self.request_factory = RequestFactory()
        get_response = MagicMock()
        self.middleware = SessionMiddleware(get_response)

        self.user = UserModel.objects.create(username="user")

        return super().setUp()

    def build_response(
        self, token_user: UserModel, request_user: Optional[UserModel] = None, token: Optional[str] = None
    ) -> Tuple[HttpRequest, TemplateResponse]:
        """
        Builds a request made by `request_user`, with url kwargs for a base64 encoded `token_user` and a `token`.
        If `token` is omitted, a valid token is generated based on the `token_user`
        """
        token = token or self.view_class.token_generator.make_token(token_user)
        uidb64 = urlsafe_base64_encode(force_bytes(token_user.pk))
        req: HttpRequest = self.request_factory.get(f"/my_path/{token}/foo/{uidb64}/bar/")
        req.user = request_user

        # Enable session middleware
        self.middleware.process_request(req)
        req.session.save()

        return req, uidb64, token

    def test_token_url_success(self):
        """Tests redirection and token handling with valid tokens"""
        req, uidb64, token = self.build_response(self.user)
        res = self.view(req, uidb64=uidb64, token=token)
        self.assertEqual(
            res.status_code, 302, "Token valid; should redirect to same page without the token in the URL"
        )
        self.assertEqual(
            req.path.replace(token, self.view_class.url_token_name), res.url, "Token should be replaced in the URL"
        )
        self.assertIn(self.view_class.session_token_name, req.session, "Session token should be set")
        self.assertEqual(req.session[self.view_class.session_token_name], token)

    def test_token_session_success(self):
        """Tests token handling with valid session tokens"""
        req, uidb64, token = self.build_response(self.user)
        req.session[self.view_class.session_token_name] = token
        res = self.view(req, uidb64=uidb64, token=self.view_class.url_token_name)
        self.assertEqual(res.status_code, 200)
        # TemplateView converts template_name into a list
        self.assertListEqual(
            res.template_name,
            [self.view_class.template_name],
            "Success template should be used when token is valid.",
        )

    def _test_token_fail(self, request: HttpRequest, response: TemplateResponse, msg: str = "Token"):
        """Common checks for failed tokens"""
        self.assertEqual(response.status_code, 400, f"{msg} is invalid; should stay on page")
        self.assertEqual(
            response.template_name,
            self.view_class.fail_template_name,
            "Fail template should be used when token is invalid.",
        )
        self.assertNotIn(
            self.view_class.session_token_name,
            request.session,
            "Session token should not be set when token is invalid",
        )

    def test_token_url_fail(self):
        """Tests token handling with invalid tokens in the URL"""
        # Token itself is invalid
        req, uidb64, token = self.build_response(self.user, token="INVALID")
        res = self.view(req, uidb64=uidb64, token=token)
        self._test_token_fail(req, res)

        # Token already replaced in URL, but not present in session data
        req, uidb64, token = self.build_response(self.user, token=self.view_class.url_token_name)
        res = self.view(req, uidb64=uidb64, token=token)
        self._test_token_fail(req, res)

    def test_token_session_fail(self):
        """Tests token handling with invalid tokens in the session"""
        # Invalid token present in session data
        req, uidb64, token = self.build_response(self.user, token=self.view_class.url_token_name)
        req.session[self.view_class.session_token_name] = "INVALID"
        res = self.view(req, uidb64=uidb64, token=token)
        self.assertEqual(res.status_code, 400, f"Token in session is invalid; should stay on page")

        self.assertEqual(
            res.template_name,
            self.view_class.fail_template_name,
            "Fail template should be used when token is invalid.",
        )

    def test_user_fail(self):
        """Tests token handling if the user in the url is invalid"""
        # Base64 text is invalid
        req, _, token = self.build_response(self.user)
        res = self.view(req, uidb64="1", token=token)
        self._test_token_fail(req, res, msg="base64 encoded user")

        # User does not exist
        req, _, token = self.build_response(self.user)
        res = self.view(req, uidb64=urlsafe_base64_encode(force_bytes(42)), token=token)
        self._test_token_fail(req, res, msg="Non-existing user")

    def test_delete_token(self):
        """Tests if token deletion works"""
        view = self.view_class()
        req = self.request_factory.get(f"/my_path/")
        view.setup(req)

        # Use session middleware
        self.middleware.process_request(req)
        req.session.save()

        # Token should be removed from session data
        req.session[self.view_class.session_token_name] = "Session token"
        view.delete_token()
        self.assertNotIn(self.view_class.session_token_name, req.session)
