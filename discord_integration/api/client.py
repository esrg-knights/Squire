from dataclasses import dataclass
import json
import logging
import requests

from django.contrib.auth import get_user_model
from django.utils import timezone

from discord_integration.api.metadata import DiscordSquireMetadata
from discord_integration.models import LinkedOAuthToken

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class OAuthTokens:
    """OAuth 2.0 tokens"""

    access_token: str
    refresh_token: str
    expires_in: str


@dataclass
class DiscordAPIClient:
    """
    Code specific to communicating with the Discord API.

    The following methods all facilitate OAuth2 communication with Discord.
    See https://discord.com/developers/docs/topics/oauth2 for more details.
    """

    client_id: str
    client_secret: str
    bot_token: str
    cookie_secret: str
    oauth_redirect_uri: str

    def _get_headers(self) -> dict:
        """Retrieves the headers required to fetch info from the Mailcow API."""
        return {
            "user-agent": "squire/1.0.0",
        }

    def get_oauth_url(self, csrf_token) -> str:
        """
        Generate the url which the user will be directed to in order to approve the
        bot, and see the list of requested scopes.
        """
        url = "https://discord.com/api/oauth2/authorize"

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.oauth_redirect_uri,
            "response_type": "code",
            "state": csrf_token,
            # Request setting role metadata and reading Discord user's profile data (except email)
            "scope": "role_connections.write identify",
            "prompt": "consent",
        }
        return requests.Request("GET", url, params=params).prepare().url

    def get_oauth_tokens(self, code: str) -> OAuthTokens:
        """
        Given an OAuth2 code from the scope approval page, make a request to Discord's
        OAuth2 service to retrieve an access token, refresh token, and expiration.

        :param: :code: Passed by the Discord API
        """
        url = "https://discord.com/api/v10/oauth2/token"
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.oauth_redirect_uri,
        }

        res = requests.post(url, body, headers={"content_type": "application/x-www-form-urlencoded"})
        print(res.content)
        print(res.status_code)
        if res.status_code == 200:
            data = res.json()
            return OAuthTokens(data["access_token"], data["refresh_token"], data["expires_in"])
        raise ValueError(f"Error fetching Discord OAuth tokens: [{res.status_code}] {res.content}")

    def get_authorization_data(self, tokens: OAuthTokens) -> dict:
        """
        Given a user based access token, fetch profile information for the current user.
        See: https://discord.com/developers/docs/topics/oauth2#get-current-authorization-information
        """
        url = "https://discord.com/api/v10/oauth2/@me"
        headers = {"Authorization": f"Bearer {tokens.access_token}"}
        res = requests.get(url, headers=headers)
        print(res.content)
        if res.status_code == 200:
            return res.json()
        raise ValueError(f"Error fetching user data: [{res.status_code}] {res.content}")

    def get_access_token(self, tokens: LinkedOAuthToken) -> str:
        """
        The initial token request comes with both an access token and a refresh
        token. Check if the access token has expired, and if it has, use the
        refresh token to acquire a new, fresh access token.
        """
        if timezone.now() <= tokens.expiry_date:
            return tokens.access_token

        url = "https://discord.com/api/v10/oauth2/token"
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": tokens.refresh_token,
        }
        res = requests.post(url, body, headers={"content_type": "application/x-www-form-urlencoded"})
        print(res.status_code)
        print(res.content)
        if res.status_code == 200:
            new_tokens = res.json()
            tokens.access_token = new_tokens["access_token"]
            tokens.refresh_token = new_tokens["refresh_token"]
            tokens.expiry_date = timezone.now() + timezone.timedelta(seconds=new_tokens["expires_in"])
            tokens.save()
            return tokens.access_token
        raise ValueError(f"Error refreshing access token: [{res.status_code}] {res.content}")

    def register_metadata(self) -> str:
        """
        Register the metadata to be stored by Discord. This should be a one time action.
        Note: uses a Bot token for authentication, not a user token.
        """
        url = f"https://discord.com/api/v10/applications/{self.client_id}/role-connections/metadata"
        body = json.dumps(DiscordSquireMetadata.as_register_json())
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bot {self.bot_token}",
        }

        res = requests.put(url, body, headers=headers)
        if res.status_code == 200:
            return res.json()
        raise ValueError(f"Error pushing discord metadata schema: [{res.status_code}] {res.content}")

    def push_metadata(self, tokens: LinkedOAuthToken, metadata: DiscordSquireMetadata) -> str:
        """Given metadata that matches the schema, push that data to Discord on behalf of the current user."""
        url = f"https://discord.com/api/v10/users/@me/applications/{self.client_id}/role-connection"
        access_token = self.get_access_token(tokens)
        body = json.dumps(
            {
                "platform_name": "Squire Membership",
                "metadata": metadata.as_update_json(),
            }
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        print(body)
        res = requests.put(url, body, headers=headers)
        print(res.content)
        print(res.status_code)
        if res.status_code == 200:
            return res.json()
        raise ValueError(f"Error pushing Discord metadata: [{res.status_code}] {res.content}")
