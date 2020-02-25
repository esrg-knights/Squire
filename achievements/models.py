from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

#Setup some constants
maxDescriptionLength = 255
maxNameLength = 31

# Create categories for the Achievements like Boardgames, Roleplay, General
class Category(models.Model):
    class Meta:
        # Enabled proper plurality
        verbose_name_plural = "categories"

    name = models.CharField(max_length=maxNameLength)
    description = models.TextField(max_length=maxDescriptionLength)

    def __str__(self):
        return self.name

# Gets or creates the default Category
def get_or_create_default_category():  
    return Category.objects.get_or_create(name='General', description='Contains Achievements that do not belong to any other Category.')[0]

# Achievements that can be earned by users
class Achievement(models.Model):
    # Basic Information
    name = models.CharField(max_length=maxNameLength)
    description = models.TextField(max_length=maxDescriptionLength)
    category = models.ForeignKey(Category, on_delete=models.SET(get_or_create_default_category), related_name="related_achievements")

    # An Achievement can be claimed by more members (claimants) and a member can have more achievements.
    claimants = models.ManyToManyField(User, blank=True, related_name="claimed_achievements")

    def __str__(self):
        return self.name
