from django.db import models
from django.contrib.auth.models import User

# Gets the display name of the user
def get_display_name(self):
    if self.first_name is not None:
        return self.first_name
    return self.username

# Register the new method
User.add_to_class("get_display_name", get_display_name)
