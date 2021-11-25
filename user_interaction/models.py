from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import PresetImage
from user_interaction.pintypes import GenericPin, PINTYPES, PinVisibility



class Pin(models.Model):
    """
    A pin is a small notification on the homepage. It can link to a specific model instance.
    """

    # Date and creator of the pin
    creation_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)


    pintype = models.CharField(
        max_length=31,
        choices=[
            (identifier, pintype.name) for (identifier, pintype) in PINTYPES.items()
        ],
        default=GenericPin
    )

    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    image = models.ForeignKey(PresetImage, on_delete=models.SET_NULL, blank=True, null=True)

    local_visibility = models.CharField(
        max_length=15,
        choices=[
            (PinVisibility.PIN_PUBLIC,        "Public"),
            (PinVisibility.PIN_USERS_ONLY,    "Any User"),
            (PinVisibility.PIN_MEMBERS_ONLY,  "Members Only"),
        ],
        help_text="Public pins can be viewed by anyone. User-only pins can be viewed by any logged in user. Members-only pins can only be viewed by (non-deregistered) members.",
        blank=True, null=True,
    )

    @property
    def visibility(self):
        if self.local_visibility is not None:
            return self.local_visibility
        return self.pintype.default_visibility

    # Visibility Requirements
    publish_date = models.DateTimeField(default=timezone.now)

    # Related Model instance (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # # Use object data as a default for the pin's title (get_pin_title), description (get_pin_description)
    # #   URL (get_absolute_url) and image (get_preview_image).
    # #   If a title, description, URL, or image is provided anyways, then those have priority over the object data.
    # use_object_data = models.BooleanField(default=True, help_text="If enabled, fetches the URL and image from the related object (unless overridden).")

    # @property
    # def title(self):
    #     if self.title:
    #         return self.title
    #     if self.use_object_data and self.content_object is not None:
    #         return str(self.content_object)
    #     return self.pintype.default_title

    # @property
    # def image(self):
    #     if self.local_image is not None:
    #         return self.local_image.image.url
    #     if self.use_object_data and self.content_object is not None:
    #         try:
    #             return self.content_object.get_preview_image()
    #         except AttributeError:
    #             pass
    #     return f'{settings.STATIC_URL}images/default_logo.png'

    # @property
    # def url(self):
    #     if self.local_url is not None:
    #         return self.local_url
    #     if self.use_object_data and self.content_object is not None:
    #         try:
    #             return self.content_object.get_absolute_url()
    #         except AttributeError:
    #             pass
    #     return None

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        # Make exlude a list to prevent complex if statements
        exclude = exclude or []

        if 'content_type' not in exclude and 'object_id' not in exclude:
            if self.content_type is not None and self.content_object is None:
                raise ValidationError("The connected instance does not exist", code='instance_nonexistent')

    # def clean(self):
    #     super().clean()

    #     # Can only upload MarkdownImages for specific models
    #     if self.content_type is not None:
    #         if f"{self.content_type.app_label}.{self.content_type.model}" not in settings.MARKDOWN_IMAGE_MODELS:
    #             raise ValidationError({'content_type': "MarkdownImages cannot be uploaded for this ContentType"})

    #     # Cannot have a content_type - object_id combination that does not exist
    #     if self.object_id is not None and self.content_object is None:
    #         raise ValidationError({'object_id': 'The selected ContentType does not have an object with this id'})

    def __str__(self):
        return f"Pin {self.id} - {self.title} ({self.content_object})"
