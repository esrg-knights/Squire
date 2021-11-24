from django.apps import AppConfig
from django.contrib.auth import get_user_model

class UserInteractionConfig(AppConfig):
    name = 'user_interaction'

    def ready(self):
        from membership_file.util import get_member_from_user

        def _get_user_display_name(user):
            """
                Describes how a user should be displayed throughout the entire application

                If the user is a member:
                - <first name> <?tussenvoegsel> <lastname>

                If the user is not a member:
                - No real name set: <username>
                - Real name set: <first_name>
            """
            member = get_member_from_user(user)
            if member is not None:
                return member.get_full_name()
            return (user.first_name or user.username)

        # Monkey-patch the user model's string method
        User = get_user_model()
        User.add_to_class('__str__', _get_user_display_name)
