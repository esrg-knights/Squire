from typing import Any, Dict
from django import http
from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms.models import BaseModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.views import View
from django.views.generic import TemplateView, FormView, DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, UpdateView, ModelFormMixin, FormView
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import override as translation_override
from dynamic_preferences.registries import global_preferences_registry
from core.views import LinkedLoginView, RegisterUserView
from utils.tokens import SessionTokenMixin, UrlTokenMixin
from utils.views import ModelAdminFormViewMixin

UserModel = get_user_model()

# Enable the auto-creation of logs
from membership_file.auto_model_update import *
from membership_file.export import *
from membership_file.forms import (
    ConfirmLinkMembershipLoginForm,
    ConfirmLinkMembershipRegisterForm,
    ContinueMembershipForm,
    RegisterMemberForm,
    ResendRegistrationForm,
)
from membership_file.models import MemberYear, Membership, Room
from membership_file.util import LinkAccountTokenGenerator, MembershipRequiredMixin

global_preferences = global_preferences_registry.manager()


class MemberMixin(MembershipRequiredMixin):
    """
    Sets the view's object to the Member corresponding to the user that makes
    the request.
    """

    def get_object(self, queryset=None):
        return self.request.member


# Page that loads whenever a user tries to access a member-page
class NotAMemberView(TemplateView):
    template_name = "membership_file/no_member.html"


class UpdateMemberYearMixin:
    year = None

    def setup(self, request, *args, **kwargs):
        self.year = global_preferences["membership__signup_year"]
        if self.year is None:
            raise PermissionDenied("There is no year active to extend")

        super(UpdateMemberYearMixin, self).setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UpdateMemberYearMixin, self).get_context_data(**kwargs)
        context["new_year"] = self.year
        return context


class ExtendMembershipView(MemberMixin, UpdateMemberYearMixin, FormView):
    template_name = "membership_file/extend_membership.html"
    form_class = ContinueMembershipForm
    success_url = reverse_lazy("membership:continue_success")

    def dispatch(self, request, *args, **kwargs):
        if Membership.objects.filter(year=self.year, member=self.request.member).exists():
            return TemplateResponse(
                request,
                template="membership_file/extend_membership_already_done.html",
                context=self.get_context_data(),
            )

        return super(ExtendMembershipView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ExtendMembershipView, self).get_form_kwargs()
        kwargs.update({"member": self.request.member, "year": self.year})
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = f"Successfully extended Knights membership into {self.year}"
        messages.success(self.request, msg)
        return super(ExtendMembershipView, self).form_valid(form)


class ExtendMembershipSuccessView(MemberMixin, UpdateMemberYearMixin, TemplateView):
    template_name = "membership_file/extend_membership_successpage.html"


LINK_TOKEN_GENERATOR = LinkAccountTokenGenerator()


class MemberRegistrationFormMixin(PermissionRequiredMixin):
    """Mixin used to render member registration forms"""

    permission_required = "membership_file.add_member"
    token_generator = LINK_TOKEN_GENERATOR

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "request": self.request,
                "token_generator": self.token_generator,
            }
        )
        return kwargs


class RegisterNewMemberAdminView(MemberRegistrationFormMixin, ModelAdminFormViewMixin, CreateView):
    """
    A form in the admin panel that registers a new user, and optionally
    sends them a registration email. The receiver can use this registration
    email in order to link the created membership data to a new or pre-existing
    account.
    """

    form_class = RegisterMemberForm
    title = "Register new member"
    save_button_title = "Register Member"

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.email_sent = form.cleaned_data["do_send_registration_email"]
        res = super().form_valid(form)

        # Construct admin log entry
        message = self.model_admin.construct_change_message(self.request, form, None, True)
        with translation_override(None):
            for q in [
                Room.objects.filter(id__in=form.cleaned_data.get("room_access", [])),
                MemberYear.objects.filter(id__in=form.cleaned_data.get("active_years", [])),
            ]:
                for added_object in q:
                    message.append(
                        {"added": {"name": str(added_object._meta.verbose_name), "object": str(added_object)}}
                    )
        self.model_admin.log_addition(self.request, self.object, message)
        return res

    def get_success_url(self) -> str:
        # Send user back to the member registration form, and show a message with a link to the newly created member object
        member_link = reverse(f"admin:membership_file_member_change", args=(self.object.id,))
        if self.email_sent:
            messages.success(
                self.request,
                format_html('Registered and emailed member “<a href="{1}">{0}</a>”', self.object, member_link),
            )
        else:
            messages.warning(
                self.request,
                format_html('Registered, but did not email member “<a href="{1}">{0}</a>”', self.object, member_link),
            )
        return reverse(f"admin:membership_file_member_actions", args=("register_new_member",))


class ResendRegistrationMailAdminView(MemberRegistrationFormMixin, ModelAdminFormViewMixin, UpdateView):
    """TODO
    Object is derived from <pk> in the URLConf
    """

    form_class = ResendRegistrationForm
    model = form_class._meta.model
    template_name = "membership_file/resend_registration_email.html"
    title = "Re-send membership email"
    save_button_title = "Resend email"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        res = super().dispatch(request, *args, **kwargs)
        if self.object.user is not None:
            return HttpResponseBadRequest("Member already has an associated user.")
        return res

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_success_url(self) -> str:
        member_link = reverse(f"admin:membership_file_member_change", args=(self.object.id,))
        messages.success(
            self.request,
            format_html('Re-sent registration email to member “<a href="{1}">{0}</a>”', self.object, member_link),
        )
        return member_link


class LinkMembershipViewTokenMixin:
    """
    A mixin to be used in combination with `UrlTokenMixin` or `SessionTokenMixin`.
    It is able to generate (and verify) tokens for Member objects for the purpose
    of linking a Member to some user.

    This linking should fail if a member already has an associated user, or if
    the request's user already has an associated member.
    """

    fail_template_name = "core/user_accounts/link_fail.html"
    session_token_name = "_link_account_token"
    token_generator = LINK_TOKEN_GENERATOR

    object_class = Member

    def get_url_object(self, uidb64: str):
        member = super().get_url_object(uidb64)
        # If the member already has an associated user, then abort
        if member is not None and member.user is not None:
            return None
        return member

    def dispatch(self, *args, **kwargs):
        # Fail if the requesting user already has a member
        if hasattr(self.request.user, "member"):
            return self.token_invalid()
        return super().dispatch(*args, **kwargs)


class LinkMembershipConfirmView(LinkMembershipViewTokenMixin, UrlTokenMixin, View):
    """
    This view is the starting point for linking a member to a user. It (verifies and ) stores
    a token from the URL in the session data, and redirects to other views to handle the linking
    process.

    If a user is already logged in, the user is redirected to a login view. Otherwise, they are
    redirected to a registration page where they can create a new Squire account.
    """

    url_token_name = "link-account"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            # Already logged in
            return HttpResponseRedirect(
                reverse("membership:link_account/login", args=(kwargs[self.object_id_kwarg_name],))
            )
        # Create a new account
        return HttpResponseRedirect(
            reverse("membership:link_account/register", args=(kwargs[self.object_id_kwarg_name],))
        )


class LinkMembershipRegisterView(LinkMembershipViewTokenMixin, SessionTokenMixin, RegisterUserView):
    """
    Shows a registration form which, when filled, registers a new user and attaches a predetermined
    member to it. This also prefills some of the user registration form fields based on the member's data.
    """

    form_class = ConfirmLinkMembershipRegisterForm
    post_link_login = True
    post_link_login_backend = "django.contrib.auth.backends.ModelBackend"
    success_url = reverse_lazy("account:membership:view")

    def dispatch(self, *args, **kwargs):
        # Fail if a user is logged in
        if self.request.user.is_authenticated:
            return self.token_invalid(status=403)
        return super().dispatch(*args, **kwargs)

    def get_login_url(self):
        return reverse("membership:link_account/login", args=(self.kwargs[self.object_id_kwarg_name],))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["member"] = self.url_object
        # Prefill some form fields
        kwargs["initial"] = {
            "first_name": self.url_object.get_full_name(allow_spoof=False),
            "email": self.url_object.email,
        }
        return kwargs

    def form_valid(self, form: ConfirmLinkMembershipRegisterForm):
        res = super().form_valid(form)
        # UserCreationForm saves form with commit=False, so we need to call save_m2m ourselves
        form.save_m2m()
        self.delete_token()
        if self.post_link_login:
            auth_login(self.request, self.object, self.post_link_login_backend)

        messages.success(self.request, "Membership data linked successfully!")
        return res


class LinkMembershipLoginView(LinkMembershipViewTokenMixin, SessionTokenMixin, LinkedLoginView):
    """
    Shows a login form which, when filled, attached a predetermined member to the user that was logged in.
    If a user is already logged in, they should still enter their credentials.
    TODO: Skip asking for login credentials if the user had already logged in very recently (e.g. 5 minutes ago)
    """

    authentication_form = ConfirmLinkMembershipLoginForm
    success_url = reverse_lazy("account:membership:view")

    link_title = "Link Membership Data"
    link_extra = "This will also update your Squire account's email and real name."

    def get_link_description(self):
        return format_html(
            "Logging in will automatically link membership data for <i>{0}</i> to your account.",
            self.url_object.get_full_name(allow_spoof=False),
        )

    def get_register_url(self):
        # Show a link to the registration page if the user is not authenticated.
        if self.request.user.is_authenticated:
            return None
        return reverse("membership:link_account/register", args=(self.kwargs[self.object_id_kwarg_name],))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["member"] = self.url_object
        if self.request.user.is_authenticated:
            # Prefill some form fields
            kwargs["initial"] = {
                "username": self.request.user.username,
            }
        return kwargs

    def form_valid(self, form: ConfirmLinkMembershipLoginForm):
        # If the logged in user already has an attached member, abort
        if hasattr(form.get_user(), "member"):
            messages.error(self.request, "This account already has a linked member.")
            # Logout user, but keep the token (session data is flushed)
            token = self.request.session[self.session_token_name]
            auth_logout(self.request)
            self.request.session[self.session_token_name] = token
            return self.render_to_response(self.get_context_data())

        form.save()
        self.delete_token()
        messages.success(self.request, "Membership data linked successfully!")
        return super().form_valid(form)

    def get_redirect_url(self) -> str:
        return self.success_url
