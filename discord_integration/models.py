from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class LinkedOAuthToken(models.Model):
    """OAuth2 token storage, linked to a specific web service and Squire user"""

    class Meta:
        constraints = (models.UniqueConstraint(fields=["name", "user"], name="unique user for web service"),)

    # Must not be mutable; see https://docs.djangoproject.com/en/5.1/ref/models/fields/#django.db.models.Field.default
    def metadata_default():
        return {}

    # NB: Do not limit token length
    access_token = models.TextField()
    refresh_token = models.TextField()
    expiry_date = models.DateTimeField()

    name = models.CharField(max_length=256)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oauth_tokens")
    # Additional metadata to store. E.g. Discord account name
    metadata = models.JSONField(encoder=DjangoJSONEncoder, default=metadata_default)

    def __str__(self):
        return f"{self.name} oAuth2 token for {self.user}"
