from django.db import models
from django.utils import timezone

# Create categories for the Achievements like Boardgames, Roleplay, General
class Category(models.Model):
    name = models.CharField(max_length=31)
    description = models.TextField(max_length=255)

    def __str__(self):
        return self.name

# The Achievement model represents the achievements in the achievements file.
class Achievement(models.Model):
    # Different achievements can have the same category, but every Achievement can only have one category.
    category = models.ForeignKey(Category, on_delete = models.SET_DEFAULT, default=1, blank = True, related_name = "related_category")

    name = models.CharField(max_length=31)
    description = models.TextField(max_length=255)
    # An Achievement can be claimed by more members (claimants) and a member can have more achievements.
    claimants = models.ManyToManyField(Member); # TODO: Add when Member model is added

    def __str__(self):
        return self.name
