from functools import partial
from typing import Any, Dict, Optional, Type
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.admin import helpers, ModelAdmin
from django.core.exceptions import PermissionDenied
from django.db.models import Model
from django.forms import ValidationError
from django.forms.models import BaseModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView, FormView
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_decode
from dynamic_preferences.registries import global_preferences_registry
from core.views import LoginView, RegisterUserView

UserModel = get_user_model()

# Enable the auto-creation of logs
from membership_file.auto_model_update import *
from membership_file.export import *
from membership_file.forms import (
    ConfirmLinkMembershipLoginForm,
    ConfirmLinkMembershipRegisterForm,
    ContinueMembershipForm,
    RegisterMemberForm,
)
from membership_file.models import Membership
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
        msg = f"Succesfully extended Knights membership into {self.year}"
        messages.success(self.request, msg)
        return super(ExtendMembershipView, self).form_valid(form)


class ExtendMembershipSuccessView(MemberMixin, UpdateMemberYearMixin, TemplateView):
    template_name = "membership_file/extend_membership_successpage.html"


class ModelAdminFormViewMixin:
    """TODO"""

    # Class variable needed as we need to be able to pass this through as_view(..)
    model_admin: ModelAdmin = None

    def __init__(self, *args, model_admin: ModelAdmin = None, **kwargs) -> None:
        assert model_admin is not None
        self.model_admin = model_admin
        super().__init__(*args, **kwargs)

    def get_form(self, form_class: Optional[type[BaseModelForm]] = None) -> BaseModelForm:
        # This method should return a form instance
        if form_class is None:
            form_class = self.get_form_class()

        # Use this form_class's excludes instead of those from the ModelAdmin's form_class
        exclude = form_class._meta.exclude or ()

        # This constructs a form class
        # NB: More defaults can be passed into the **kwargs of ModelAdmin.get_form
        form_class = self.model_admin.get_form(
            self.request,
            None,
            change=False,
            # Fields are defined in the form
            fields=None,
            # Override standard ModelAdmin form and ignore its exclude list
            form=form_class,
            exclude=exclude,
        )

        # Use the newly constructed form class to create a form
        return super().get_form(form_class)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        form: RegisterMemberForm = context.pop("form")
        adminForm = helpers.AdminForm(
            form, list(form.get_fieldsets(self.request, self.object)), {}, model_admin=self.model_admin
        )

        context.update(
            {
                "adminform": adminForm,
                # 'form_url': form_url,
                "is_nav_sidebar_enabled": True,
                "opts": Member._meta,
                "title": "Register new member",
                # 'content_type_id': get_content_type_for_model(self.model).pk,
                # 'app_label': app_label,
            }
        )

        return context


LINK_TOKEN_GENERATOR = LinkAccountTokenGenerator()


class RegisterNewMemberAdminView(ModelAdminFormViewMixin, CreateView):
    """TODO"""

    form_class = RegisterMemberForm
    template_name = "membership_file/register_member.html"
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

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.email_sent = form.cleaned_data["send_registration_email"]
        return super().form_valid(form)

    def get_success_url(self) -> str:
        if self.email_sent:
            messages.success(self.request, f"Registered and emailed member “{self.object}”")
        else:
            messages.warning(self.request, f"Registered, but did not email member “{self.object}”")

        return reverse(f"admin:membership_file_member_change", args=(self.object.id,))


class TokenMixinBase:
    """TODO"""

    # Subclasses should override this
    fail_template_name = "fail_template_name: TokenMixin fail placeholder"
    session_token_name: str = None
    token_generator: PasswordResetTokenGenerator = None
    object_id_kwarg_name = "uidb64"
    object_class: Type[Model] = UserModel

    def get_url_object(self, uidb64: str):
        """Equivalent to get_user"""
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            url_object = self.object_class._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, self.object_class.DoesNotExist, ValidationError):
            url_object = None
        return url_object

    def delete_token(self):
        """TODO"""
        del self.request.session[self.session_token_name]

    def dispatch(self, *args, **kwargs):
        if not self.validlink:
            return render(self.request, self.fail_template_name)
        return super().dispatch(*args, **kwargs)


class UrlTokenMixin(TokenMixinBase):
    """Converts a URL token to a session token"""

    # Subclasses should override this
    url_token_name: str = None

    token_kwarg_name = "token"
    object_class: Type[Model] = UserModel

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert self.object_id_kwarg_name in kwargs and self.token_kwarg_name in kwargs

        self.validlink = False
        self.url_object = self.get_url_object(kwargs[self.object_id_kwarg_name])

        # View is only valid if a url object was passed
        if self.url_object is not None:
            token = kwargs[self.token_kwarg_name]
            if token == self.url_token_name:
                session_token = self.request.session.get(self.session_token_name)
                if self.token_generator.check_token(self.url_object, session_token):
                    # If the token is valid, display the link account form.
                    self.validlink = True
                    return super().dispatch(*args, **kwargs)
            else:
                if self.token_generator.check_token(self.url_object, token):
                    # Store the token in the session and redirect to the
                    # link account form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.
                    self.request.session[self.session_token_name] = token
                    redirect_url = self.request.path.replace(token, self.url_token_name)
                    return HttpResponseRedirect(redirect_url)

        # Token was invalid
        return super().dispatch(*args, **kwargs)


class SessionTokenMixin(TokenMixinBase):
    """Uses a session token"""

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert self.object_id_kwarg_name in kwargs

        self.validlink = False
        self.url_object = self.get_url_object(kwargs[self.object_id_kwarg_name])

        # View is only valid if a url object was passed
        if self.url_object is not None:
            session_token = self.request.session.get(self.session_token_name)
            if self.token_generator.check_token(self.url_object, session_token):
                # If the token is valid, display the link account form.
                self.validlink = True
                return super().dispatch(*args, **kwargs)

        return super().dispatch(*args, **kwargs)


class LinkMembershipViewTokenMixin:
    """TODO"""

    fail_template_name = "membership_file/user_accounts/link_fail.html"
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
        res = super().dispatch(*args, **kwargs)
        # Fail if the requesting user already has a member
        if hasattr(self.request.user, "member"):
            return render(self.request, self.fail_template_name)
        return res



class LinkMembershipConfirmView(LinkMembershipViewTokenMixin, UrlTokenMixin, View):
    """
    `self.url_token_name` is the equivalent of reset_url_token in PasswordResetConfirmView
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
    Shows a registration form which, when filled, registers a new user and
    attached a predetermined member to it.
    """

    form_class = ConfirmLinkMembershipRegisterForm
    post_link_login = True
    post_link_login_backend = "django.contrib.auth.backends.ModelBackend"
    success_url = reverse_lazy("account:membership:view")

    def dispatch(self, *args, **kwargs):
        res = super().dispatch(*args, **kwargs)
        # Fail if a user is logged in
        if self.request.user.is_authenticated:
            return render(self.request, self.fail_template_name)
        return res

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
        user = form.save(commit=False)
        # UserCreationForm saves form with commit=False, so we need to call save_m2m ourselves
        user.save()
        form.save_m2m()
        self.delete_token()
        if self.post_link_login:
            auth_login(self.request, user, self.post_link_login_backend)

        messages.success(self.request, "Membership data linked successfully!")
        return super().form_valid(form)


class LinkedLoginView(LoginView):
    """TODO"""

    image_source = None
    image_alt = None
    link_title = None
    link_description = None
    link_extra = None

    def get_image_source(self):
        """TODO"""
        return self.image_source

    def get_image_alt(self):
        """TODO"""
        return self.image_alt

    def get_link_title(self):
        """TODO"""
        return self.link_title

    def get_link_description(self):
        """TODO"""
        return self.link_description

    def get_link_extra(self):
        """TODO"""
        return self.link_extra

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "image_source": self.get_image_source(),
                "image_alt": self.get_image_alt(),
                "link_title": self.get_link_title(),
                "link_description": self.get_link_description(),
                "link_extra": self.get_link_extra(),
            }
        )
        return context

class LinkMembershipLoginView(LinkMembershipViewTokenMixin, SessionTokenMixin, LinkedLoginView):
    """
    Shows a login form which, when filled, attached a predetermined member to the user that was logged in.
    TODO: Skip asking for login credentials if the user had already logged in very recently (e.g. 5 minutes ago)
    """

    authentication_form = ConfirmLinkMembershipLoginForm
    success_url = reverse_lazy("account:membership:view")
    template_name = "membership_file/user_accounts/login_linked.html"

    link_title = "Link Membership Data"
    link_extra = "This will also update your Squire account's email and real name."

    def get_link_description(self):
        return format_html("Logging in will automatically link membership data for <i>{0}</i> to your account.", self.url_object.get_full_name(allow_spoof=False))

    def get_register_url(self):
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
        form.save()
        messages.success(self.request, "Membership data linked successfully!")
        return super().form_valid(form)

    def get_redirect_url(self) -> str:
        return self.success_url
