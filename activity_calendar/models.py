from django.conf import settings
from django.db import models
from django.utils import timezone

# Models related to the Calendar-functionality of the application.
# @author E.M.A. Arts
# @since 29 JUN 2019


# The Activity model represents an activity in the calendar
class Activity(models.Model):
    # The User that created the activity
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # The title of the activity
    title = models.CharField(max_length=200)
    
    # The description of the activity
    description = models.TextField()
    
    # The date at which the activity was created
    created_date = models.DateTimeField(default=timezone.now)
    
    # The date at which the activity will become visible for all users
    published_date = models.DateTimeField(blank=True, null=True)

    # Publishes the activity, making it visible for all users
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    # String-representation of an instance of the model
    def __str__(self):
        return "{1} ({0})".format(self.id, self.title)