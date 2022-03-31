from django.apps import AppConfig
from django.contrib.auth import get_user_model

class UserInteractionConfig(AppConfig):
    name = 'user_interaction'

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
            if global_preferences['homepage__april_2022']:
                namelist = []
                # Members
                if member is not None:
                    if member.first_name in ["Laura", "Dennis", "Denise"]:
                        namelist.append("Sjors")
                    elif len(member.first_name) % 2 == 0:
                        namelist.append("Dennis")
                    else:
                        namelist.append("Laura")

                    if member.tussenvoegsel:
                        namelist.append(member.tussenvoegsel)

                    namelist.append(member.last_name)
                else:
                    # Non-members
                    namelist = (user.first_name or user.username).split()
                    if namelist[0] in ["Laura", "Dennis", "Denise"]:
                        namelist[0] = "Sjors"
                    elif len(namelist[0]) % 2 == 0:
                        namelist[0] = "Dennis"
                    else:
                        namelist[0] = "Laura"
                return " ".join(namelist)
            ################
            # END APRIL 2022
            ################

            if member is not None:
                return member.get_full_name()
            return (user.first_name or user.username)

        # Monkey-patch the user model's string method
        User = get_user_model()
        User.add_to_class('__str__', _get_user_display_name)
