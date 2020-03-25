from django.db import models
from django.contrib.auth.models import User

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
