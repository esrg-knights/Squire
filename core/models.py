import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.utils.text import slugify

# Proxy model based on Django's user that provides extra utility methods.
class ExtendedUser(User):
    class Meta:
        proxy = True

    # Gets the display name of the user
    def get_display_name(self):
        return self.display_name_method()

    # Simplistic and default way to display a user
    def get_simple_display_name(self):
        if self.first_name:
            return self.first_name
        return self.username

    # Stores the method used to display a user's name
    display_name_method = get_simple_display_name

    # Allows other modules to change the way a user is displayed across the entire application
    @staticmethod
    def set_display_name_method(method):
        ExtendedUser.display_name_method = method

    def __str__(self):
        return self.get_display_name()


# File path to upload achievement images to
def get_image_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    # file will be uploaded to MEDIA_ROOT / presets/<achievement_id>.<file_extension>
    return 'images/presets/{0}{1}'.format(slugify(instance.name), extension)


class PresetImageManager(models.Manager):
    def for_user(self, user):
        if user.has_perm('core.can_select_presetimage_any'):
            return self.get_queryset()
        return self.get_queryset().filter(selectable=True)

# A general model allowing the storage of images
class PresetImage(models.Model):
    class Meta:
        permissions = [
            ('can_select_presetimage_any',  "[F] Can choose PresetImages that are normally not selectable."),
        ]

    objects = PresetImageManager()

    name = models.CharField(max_length=63)
    image = models.ImageField(upload_to=get_image_upload_path)
    selectable = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.id})"


# Specifies the upload path for MarkdownImages
#   This could not be defined in the class itself due to a self-reference at initalisation
def _get_markdown_image_upload_path_for_instance(instance, filename):
    file_extension = os.path.splitext(filename)[1]
    img_uuid = "{0}{1}".format(uuid.uuid4().hex[:10], file_extension)
    storage_path = os.path.join(settings.MARTOR_UPLOAD_PATH, str(instance.uploader.id), img_uuid)

    # storage_path: MEDIA_ROOT/uploads/<uploader_id>/<uuid>.<file_extension>
    return storage_path

# Each instance represents an image uploaded in Martor's markdown editor
# This allows admins to easily delete these images
class MarkdownImage(models.Model):
    class Meta():
        permissions = [
            ("can_upload_martor_images", "Can upload images using the Martor Markdown editor"),
        ]

    # Date and uploader of the image
    upload_date = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to=_get_markdown_image_upload_path_for_instance)

    # Object that uses this MarkdownImage (E.g. an Activity or ActivityMoment)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    def clean(self):
        super().clean()

        # Can only upload MarkdownImages for specific models
        if self.content_type is not None:
            if f"{self.content_type.app_label}.{self.content_type.model}" not in settings.MARKDOWN_IMAGE_MODELS:
                raise ValidationError({'content_type': "MarkdownImages cannot be uploaded for this ContentType"})

        # Cannot have a content_type - object_id combination that does not exist
        if self.object_id is not None and self.content_object is None:
            raise ValidationError({'object_id': 'The selected ContentType does not have an object with this id'})

    def __str__(self):
        return f"{self.content_type}-MarkdownImage ({self.id})"
