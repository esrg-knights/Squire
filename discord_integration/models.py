from django.conf import settings
from django.db import models


class LinkedOAuthToken(models.Model):
    """OAuth2 token storage, linked to a specific web service and Squire user"""

    class Meta:
        constraints = (models.UniqueConstraint(fields=["name", "user"], name="unique user for web service"),)

    # NB: Do not limit token length
    access_token = models.TextField()
    refresh_token = models.TextField()
    expiry_date = models.DateTimeField()

    name = models.CharField(max_length=32)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oauth_tokens")

    def __str__(self):
        return f"{self.name} oAuth2 token for {self.user}"
