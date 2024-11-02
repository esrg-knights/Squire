import json
from typing import Any, Optional
import uuid

from django import http
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login as auth_login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.utils import timezone
from core.forms import LoginForm

from core.views import LinkedLoginView
from discord_integration.api.client import DiscordAPIClient
from discord_integration.api.metadata import DiscordSquireMetadata
from discord_integration.models import LinkedOAuthToken


class DiscordSettings:
    """
    TODO: Merge properly with Mailcowconfig.json and its settings.
    Rename settings_mailcow to settings_prod?
    This class is purely for quick prototyping.
    """

    @classmethod
    def get_client(cls):
        with open("squire/config/discordconfig.json", "r") as dconfig:
            data = json.load(dconfig)
        return DiscordAPIClient(
            data["DISCORD_CLIENT_ID"],
            data["DISCORD_CLIENT_SECRET"],
            data["DISCORD_TOKEN"],
            data["COOKIE_SECRET"],
            data["DISCORD_REDIRECT_URI"],
        )


class DiscordLinkedRoleLoginView(LinkedLoginView):
    """
    Route configured in the Discord developer console which facilitates the
    connection between Discord and Squire.
    To start the flow, generate the OAuth2 consent dialog url for Discord,
    and redirect the user there.
    Before continuing back to Discord, requires the user to login.
    """

    register_url = None
    link_title = "Link Discord"
    link_description = "This will link your Squire account to Discord. This does not share personal data."
    link_extra = "You will be sent back to Discord to authorize after logging in."
    image_source = "images/discord-logo-blue.png"
    image_alt = "Discord logo"

    def __init__(self, **kwargs: Any) -> None:
        self._client = DiscordSettings.get_client()
        super().__init__(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_authenticated:
            kwargs["initial"] = {"username": self.request.user.username}
        return kwargs

    def form_valid(self, form: LoginForm) -> HttpResponse:
        """TODO"""
        # NB: Cannot get user that logged in in the next view. Move authentication code there?
        # TODO: If user is already logged in in Squire, then we can even skip the authentication part?

        # If a user was already logged in before accessing this view, keep them logged in for the normal duration
        was_authenticated_before_login = self.request.user.is_authenticated

        auth_login(self.request, form.get_user())

        if not was_authenticated_before_login:
            # Otherwise expire session after 5 minutes
            self.request.session.set_expiry(60 * 5)

        print("Requesting user in DiscordOAuthCallbackView form_valid()")
        print(self.request.user)

        csrf_token = str(uuid.uuid4())
        # Store the signed state param in the user's cookies so we can verify the value later.
        #   See: https://discord.com/developers/docs/topics/oauth2#state-and-security
        res = HttpResponseRedirect(self._client.get_oauth_url(csrf_token))
        res.set_signed_cookie("clientState", csrf_token, salt=self._client.cookie_secret, max_age=1000 * 60 * 5)
        return res

    # def get(self, request: http.HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponse:
    #     # Discord expects a 'clientState' attribute as a CSRF token, which is also encoded directly in the url
    #     res = super().get(request, *args, **kwargs)

    #     print("Requesting user in DiscordLinkedRoleView get()")
    #     print(request.user)

    #     print(request.headers)
    #     print(request.META.get("HTTP_ORIGIN"))
    #     # print(request.META)
    #     print(request.get_host())
    #     return res


class DiscordOAuthCallbackView(TemplateView):
    """
    Route configured in the Discord developer console, the redirect Url to which
    the user is sent after approving the bot for their Discord account. This
    completes a few steps:
    1. Uses the code to acquire Discord OAuth2 tokens
    2. Uses the Discord Access Token to fetch the user profile
    3. Stores the OAuth2 Discord Tokens in the database
    4. Lets the user know it's all good and to go back to Discord
    """

    template_name = "discord_integration/temp.html"

    def __init__(self, **kwargs: Any) -> None:
        self._client = DiscordSettings.get_client()
        super().__init__(**kwargs)

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        # 1. Uses the code and state to acquire Discord OAuth2 tokens
        csrf_token = request.get_signed_cookie("clientState", None, self._client.cookie_secret, max_age=1000 * 60 * 5)
        # CSRF ("state") token shouldn't be modified
        if csrf_token is None or csrf_token != request.GET.get("state", None):
            raise PermissionDenied("State verification failed")

        if not self.request.user.is_authenticated:
            # TODO: Proper handling; possibly use separate template to show status to user
            raise Exception("Django session expired")

        tokens = self._client.get_oauth_tokens(request.GET.get("code"))

        # 2. Uses the Discord Access Token to fetch the user profile
        userdata = self._client.get_authorization_data(tokens).get("user", {})
        print(f"userdata: {userdata}")

        metadata = {
            "user_id": userdata.get("id"),
            "username": userdata.get("username"),
            "global_name": userdata.get("global_name"),
            "avatar_hash": userdata.get(
                "avatar"
            ),  # https://cdn.discordapp.com/avatars/<user_id>/<avatar_id>.png?size=64
            "color": userdata.get("accent_color"),
        }

        data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expiry_date": timezone.now() + timezone.timedelta(seconds=tokens.expires_in),
            "metadata": metadata,
        }
        tokens, _ = LinkedOAuthToken.objects.update_or_create(name="discord", user=self.request.user, defaults=data)

        # 3. Update the users metadata, assuming future updates will be posted to the `/update-metadata` endpoint
        metadata = DiscordSquireMetadata(
            True,
            self.request.user.is_staff,
            self.request.user.is_superuser,
            False,
        )
        self._client.push_metadata(tokens, metadata)
        # res.send('You did it!  Now go back to Discord.');

        return super().get(request, *args, **kwargs)
