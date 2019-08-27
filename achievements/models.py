from django.db import models
from django.utils import timezone
from membership_file.models import Member

#Setup some constants
maxDescriptionLength = 255
maxNameLength = 31

# Create categories for the Achievements like Boardgames, Roleplay, General
class Category(models.Model):
    name = models.CharField(max_length=maxNameLength)
    description = models.TextField(max_length=maxDescriptionLength)

    def __str__(self):
        return self.name

# The Achievement model represents the achievements in the achievements file.
class Achievement(models.Model):
    # Different achievements can have the same category, but every Achievement can only have one category.
    category = models.ForeignKey(Category, on_delete = models.SET_DEFAULT, default=1, blank = True, related_name = "related_achievements")

    name = models.CharField(max_length=maxNameLength)
    description = models.TextField(max_length=maxDescriptionLength)

    # An Achievement can be claimed by more members (claimants) and a member can have more achievements.
    claimants = models.ManyToManyField(Member, blank = True)

    def __str__(self):
        return self.name
