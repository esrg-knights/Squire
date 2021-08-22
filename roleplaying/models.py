import os

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.forms.widgets import Textarea
from django.utils.text import slugify

from core.fields import MarkdownTextField
from inventory.models import Item


__all__ = ['RoleplayingSystem', 'RoleplayingItem',]


# File path to upload achievement images to
def get_system_image_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    system_name = f'{instance.id}-{slugify(instance.name)}'

    # file will be uploaded to MEDIA_ROOT / images/item/<item_type>/<id>.<file_extension>
    return 'images/roleplaying/system/{system_name}{extension}'.format(
        system_name=system_name,
        extension=extension,
    )

class RoleplayingSystem(models.Model):
    name = models.CharField(max_length=128)
    short_description = models.CharField(max_length=128)
    long_description = MarkdownTextField(blank=True, null=True)

    image = models.ImageField(upload_to=get_system_image_upload_path, null=True, blank=True)
    is_public = models.BooleanField(default=False, verbose_name="On Systems page",
                                    help_text="Whether this system should be displayed on the roleplaying systems page")

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
    dice = models.CharField(max_length=64, null=True, blank=True)

    more_info_url = models.URLField(blank=True, null=True)

    # Relations
    achievements = GenericRelation('achievements.AchievementItemLink')

    def __str__(self):
        return self.name

# File path to upload achievement images to
def get_roleplay_item_file_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    if instance.system:
        filename = f'{instance.system.id}-{instance.id}-{slugify(instance.name)}'
    else:
        filename = f'None-{instance.id}-{slugify(instance.name)}'

    # file will be uploaded to MEDIA_ROOT / images/item/<item_type>/<id>.<file_extension>
    return 'local_only/files/item/roleplay/{filename}{extension}'.format(
        filename=filename,
        extension=extension,
    )

class RoleplayingItem(Item):
    system = models.ForeignKey(RoleplayingSystem, related_name='items',
                              on_delete=models.SET_NULL, null=True, blank=True)

    local_file = models.FileField(null=True, blank=True, upload_to=get_roleplay_item_file_upload_path)
    # The filename of the downloaded file (not the name of the local file)
    local_file_name = models.CharField(max_length=32, blank=True, null=True, verbose_name="Filename (without extension)")

    external_file_url = models.URLField(max_length=256, blank=True, null=True)

    def clean(self):
        if self.local_file and self.external_file_url:
            raise ValidationError(
                "You can not set both a digital file and an external file location",
                code='duplicate_location'
            )
