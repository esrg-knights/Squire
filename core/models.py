import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
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
        if user.has_perm('achievements.can_select_presetimage_any'):
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
