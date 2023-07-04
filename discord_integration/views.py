import json
from typing import Any, Optional
import uuid

from django import http
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login as auth_login
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import FormView
from django.utils import timezone
from core.forms import LoginForm

from core.views import LoginView
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
        with open("squire/discordconfig.json", "r") as dconfig:
            data = json.load(dconfig)
        return DiscordAPIClient(
            data["DISCORD_CLIENT_ID"],
            data["DISCORD_CLIENT_SECRET"],
            data["DISCORD_TOKEN"],
            data["COOKIE_SECRET"],
            data["DISCORD_REDIRECT_URI"],
        )


class DiscordLinkedRoleLoginView(FormView):
    """
    Route configured in the Discord developer console which facilitates the
    connection between Discord and any additional services you may use.
    To start the flow, generate the OAuth2 consent dialog url for Discord,
    and redirect the user there.
    Before continueing back to Discord, requires the user to login.
    """

    template_name = "core/user_accounts/login.html"
    form_class = LoginForm

    def __init__(self, **kwargs: Any) -> None:
        self._client = DiscordSettings.get_client()
        super().__init__(**kwargs)

    def form_valid(self, form: LoginForm) -> HttpResponse:
        """TODO"""
        # NB: Cannot get user that logged in in the next view. Move authentication code there?
        # NOTE: If user is already logged in in Squire, then we can even skip the authentication part?

        # If a user was already logged in before accessing this view, keep them logged in for the normal duration
        was_authenticated_before_login = self.request.user.is_authenticated

        auth_login(self.request, form.get_user())

        if not was_authenticated_before_login:
            # Otherwise expire session after 5 minutes
            self.request.session.set_expiry(60 * 5)
            print("Session will expire early!")

        print("Requesting user in DiscordOAuthCallbackView form_valid()")
        print(self.request.user)

        csrf_token = str(uuid.uuid4())
        # Store the signed state param in the user's cookies so we can verify the value later.
        #   See: https://discord.com/developers/docs/topics/oauth2#state-and-security
        res = HttpResponseRedirect(self._client.get_oauth_url(csrf_token))
        res.set_signed_cookie("clientState", csrf_token, salt=self._client.cookie_secret, max_age=1000 * 60 * 5)
        return res

    def get_redirect_url(self, state, *args, **kwargs) -> Optional[str]:
        return self._client.get_oauth_url(state)

    def get(self, request: http.HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponse:
        # Discord expects a 'clientState' attribute as a CSRF token, which is also encoded directly in the url
        res = super().get(request, *args, **kwargs)

        print("Requesting user in DiscordLinkedRoleView get()")
        print(request.user)

        print(request.headers)
        print(request.META.get("HTTP_ORIGIN"))
        # print(request.META)
        print(request.get_host())
        return res


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
        userdata = self._client.get_user_data(tokens)

        #   {'application': {
        #      'id': '1125011599321747618',
        #       'name': 'Squire Bot',
        #       'icon': '6afd02101e5e63c6ce677301c240c9ca',
        #       'description': 'Verification of Squire identities.',
        #       'summary': '',
        #       'type': None,
        #       'hook': True,
        #       'bot_public': False,
        #       'bot_require_code_grant': False,
        #       'verify_key': '37db463d86bbc0cde205d380e1d89e01e631b7a447ac7f9fc0e5dba5b32d6b24',
        #       'flags': 0,
        #       'tags': ['squire']
        #   },
        #   'scopes': ['identify', 'role_connections.write'],
        #   'expires': '2023-07-10T18:25:39.965000+00:00',
        #   'user': {
        #       'id': '277779951363817472',
        #       'username': 'scutlet',
        #       'global_name': 'Scutlet',
        #       'avatar': '62b7592a30757791ed689361e14ad58e',
        #       'discriminator': '0',
        #       'public_flags': 256,
        #       'avatar_decoration': None
        #   }}

        data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expiry_date": timezone.now() + timezone.timedelta(seconds=tokens.expires_in),
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


#     /**
#  *
#  */
#  app.get('/discord-oauth-callback', async (req, res) => {
#   try {
#     // 1. Uses the code and state to acquire Discord OAuth2 tokens
#     const code = req.query['code'];
#     const discordState = req.query['state'];

#     // make sure the state parameter exists
#     const { clientState } = req.signedCookies;
#     if (clientState !== discordState) {
#       console.error('State verification failed.');
#       return res.sendStatus(403);
#     }

#     const tokens = await discord.getOAuthTokens(code);

#     // 2. Uses the Discord Access Token to fetch the user profile
#     const meData = await discord.getUserData(tokens);
#     const userId = meData.user.id;
#     await storage.storeDiscordTokens(userId, {
#       access_token: tokens.access_token,
#       refresh_token: tokens.refresh_token,
#       expires_at: Date.now() + tokens.expires_in * 1000,
#     });

#     // 3. Update the users metadata, assuming future updates will be posted to the `/update-metadata` endpoint
#     await updateMetadata(userId);

#     res.send('You did it!  Now go back to Discord.');
#   } catch (e) {
#     console.error(e);
#     res.sendStatus(500);
#   }
# });
