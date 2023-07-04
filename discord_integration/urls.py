from django.contrib import admin
from django.urls import path, include

from discord_integration import views

urlpatterns = [
    path("linked-role/", views.DiscordLinkedRoleLoginView.as_view(), name="linked_role"),
    path("discord-oauth-callback/", views.DiscordOAuthCallbackView.as_view(), name="discord_oauth_callback"),
    # path("update-metadata", views.viewAchievementsAll, name="metadata_update"),
]


# See: https://discord.com/developers/docs/tutorials/configuring-app-metadata-for-linked-roles
# ngrok tunnels towards a localhost. It requires an account but is useful in development.
# 1. Start ngrok: `ngrok http 8000`
# Developer Settings: https://discord.com/developers/applications/1125011599321747618/information
# 2. Set General Information > Linked roles verification URL: <ngrok url>/linked-role
# 3. Set OAuth2 > General > Redirects: <ngrok url>/discord-oauth-callback
# (4.) Add bot to a server: OAuth2 > URL Generator > Scopes: bot (then generate URL and paste it in the browser)
# 5. Modify squire/discordconfig.json with the correct callback url (it needs to match up with the one in the bot settings)
