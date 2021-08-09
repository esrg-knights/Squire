import os

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation

from inventory.models import Item


__all__ = ['RoleplayingSystem', 'RoleplayingItem',]


# File path to upload achievement images to
def get_system_image_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    # file will be uploaded to MEDIA_ROOT / images/item/<item_type>/<id>.<file_extension>
    return 'images/roleplaying/system/{system_id}{extension}'.format(
        system_id=instance.id,
        extension=extension,
    )

class RoleplayingSystem(models.Model):
    name = models.CharField(max_length=128)
    short_description = models.CharField(max_length=128)
    long_description = models.TextField(blank=True, null=True)

    image = models.ImageField(upload_to=get_system_image_upload_path, null=True, blank=True)
    is_live = models.BooleanField(default=False)

    # Other system properties
    RULE_COMPLEXITY = [
        (1, 'No rules'),
        (2, 'Rules-light'),
        (3, 'Average'),
        (4, 'Rule-heavy'),
        (5, 'Robust'),
    ]
    rate_complexity = models.IntegerField(choices=RULE_COMPLEXITY, blank=True, null=True)
    rate_lore = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
                                     blank=True, null=True)
    player_count = models.CharField(max_length=8, null=True, blank=True)
    dice = models.TextField(max_length=32, null=True, blank=True)

    # Relations
    achievements = GenericRelation('achievements.AchievementItemLink')

    def __str__(self):
        return self.name

# File path to upload achievement images to
def get_roleplay_item_file_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    # file will be uploaded to MEDIA_ROOT / images/item/<item_type>/<id>.<file_extension>
    return 'files/item/roleplay/{item_id}{extension}'.format(
        item_id=instance.id,
        extension=extension,
    )

class RoleplayingItem(Item):
    system = models.ForeignKey(RoleplayingSystem, related_name='items',
                              on_delete=models.SET_NULL, null=True, blank=True)

    digital_version = models.FileField(null=True, blank=True, upload_to=get_roleplay_item_file_upload_path)
    digital_version_file_name = models.CharField(max_length=32, null=True, blank=True)
