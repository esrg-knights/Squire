from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from inventory.models import valid_item_class_ids

from core.models import ExtendedUser as User

__all__ = ['Category', 'Achievement', 'Claimant', 'AchievementItemLink']

import os

# Create categories for the Achievements like Boardgames, Roleplay, General
class Category(models.Model):
    class Meta:
        # Enabled proper plurality
        verbose_name_plural = "categories"

        # Sort by priority, then name, then Id
        ordering = ['priority', 'name','id']

    name = models.CharField(max_length=63)
    description = models.TextField(max_length=255)
    priority = models.IntegerField(default=1)

    def __str__(self):
        return self.name

# Gets or creates the default Category
def get_or_create_default_category():
    return Category.objects.get_or_create(name='General', description='Contains Achievements that do not belong to any other Category.')[0]

# File path to upload achievement images to
def get_achievement_image_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    # file will be uploaded to MEDIA_ROOT / images/achievement_<achievement_id>.<file_extension>
    return 'images/achievements/achievement_{0}{1}'.format(slugify(instance.name), extension)

# Achievements that can be earned by users
class Achievement(models.Model):
    class Meta:
        ordering = ['name','id']
        permissions = [
            ("can_view_claimants", "[F] Can view the claimants of Achievements."),
        ]

    # Basic Information
    name = models.CharField(max_length=63)
    description = models.TextField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET(get_or_create_default_category), related_name="related_achievements")

    # An Achievement can be claimed by more members (claimants) and a member can have more achievements.
    claimants = models.ManyToManyField(User, blank=True, through="Claimant", related_name="claimant_info")

    # Achievement Icon
    image = models.ImageField(upload_to=get_achievement_image_upload_path)

    # Text used to display unlocked status. Can be used to display extra data for high scores.
    # {0} User
    # {1} Date (Sorted on descending by default)
    # {2} extra_data_1
    # {3} extra_data_2
    # {4} extra_data_3
    # E.g. {0} unlocked this achievement on {1} with a score of {2}!
    unlocked_text = models.CharField(max_length=127, default="Claimed by {0} on {1}.",
        help_text="{0}: User Display Name, {1}: Date Unlocked, {2}: Extra Data 1 (int), {3}: Extra Data 2 (string), {4}: Extra Data 3 (string)")


    # Possible sort options
    FIELD_OPTIONS = [
        ("date_unlocked",           "Unlocked Date"),
        ("extra_data_1",            "Extra Data 1"),
        ("extra_data_2",            "Extra Data 2"),
        ("extra_data_3",            "Extra Data 3"),
    ]

    # The field to sort on
    claimants_sort_field = models.CharField(
        max_length=31,
        choices=FIELD_OPTIONS,
        default='date_unlocked',
    )

    # Whether sorting should be reversed
    # False <==> Sort Descending
    claimants_sort_ascending = models.BooleanField(default=False)

    # Whether the achievement can be accessed outside the admin panel
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AchievementItemLink(models.Model):
    """ Links an achievement with an item (e.g. boardgame) """
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f'{self.achievement} linked to {self.content_object}'


# Represents a user earning an achievement
class Claimant(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_unlocked = models.DateField(default=timezone.now)

    # Extra data fields that can be used to track high-scores
    extra_data_1 = models.IntegerField(null=True, blank=True)
    extra_data_2 = models.CharField(max_length=63, null=True, blank=True)
    extra_data_3 = models.CharField(max_length=63, null=True, blank=True)

    def __str__(self):
        return f"{self.achievement} unlocked by {self.user}"
