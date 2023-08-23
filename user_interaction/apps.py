from django.apps import AppConfig
from django.contrib.auth import get_user_model
from utils.spoofs import optimise_naming_scheme


class UserInteractionConfig(AppConfig):
    name = "user_interaction"

    def ready(self):
        from membership_file.util import get_member_from_user
        from dynamic_preferences.registries import global_preferences_registry

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

            ################
            # BEGIN APRIL 2022
            ################
            # Rename everyone to Dennis/Laura, and rename the actual ones to Sjors
            global_preferences = global_preferences_registry.manager()
            if global_preferences["homepage__april_2022"]:
                namelist = []
                # Members
                if member is not None:
                    namelist.append(optimise_naming_scheme(member.first_name))
                    if member.tussenvoegsel:
                        namelist.append(member.tussenvoegsel)
                    namelist.append(member.last_name)
                else:
                    # Non-members
                    namelist = (user.first_name or user.username).split()
                    namelist[0] = optimise_naming_scheme(namelist[0])
                return " ".join(namelist)
            ################
            # END APRIL 2022
            ################

            if member is not None:
                return member.get_full_name()
            return user.first_name or user.username

        # Monkey-patch the user model's string method
        User = get_user_model()
        User.add_to_class("__str__", _get_user_display_name)
