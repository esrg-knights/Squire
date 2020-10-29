import os

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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


# Manager that only contains public groups
class PublicGroupsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_public=True)

# Django's standard group, but also provides additional fields
class ExtendedGroup(Group):
    # Normal manager
    objects = models.Manager()

    # Only contains public groups
    public_objects = PublicGroupsManager()

    # Override the automatically created link back to the superclass
    # so that we can provide a custom related_name
    group_ptr = models.OneToOneField(
        Group, on_delete=models.CASCADE,
        parent_link=True,
        related_name="group_info",
    )

    description = models.TextField(max_length=255)

    # Non-public groups are not shown in the front-end
    is_public = models.BooleanField(default=False)

    # Some models are required by the core application and are
    # referenced several times in the source code. These should
    # never be deleted!
    can_be_deleted = models.BooleanField(default=True,
        help_text="Groups that cannot be deleted are used in Squire's source code.")


# Add newly created users to the standard "User" group.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def add_to_default_group(sender, instance, created, raw, **kwargs):
    if created and not raw:
        group = ExtendedGroup.objects.get(name="Users")
        instance.groups.add(group)
