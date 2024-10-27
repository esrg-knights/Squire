from typing import Any
from django.contrib import admin


class SquireAdminSite(admin.AdminSite):
    """
    An override of Django's default AdminSite that reorders or groups together some of the modules.
    """

    site_header = "Squire Administration"
    site_title = "Squire site admin"

    def get_app_list(self, *args, **kwargs) -> list[Any]:
        app_list = super().get_app_list(*args, **kwargs)
        app_dict: dict[str, Any] = {app["app_label"]: app for app in app_list}

        # Merge dynamic preferences (global & user)
        if "dynamic_preferences" in app_dict and "dynamic_preferences_users" in app_dict:
            app_dict["dynamic_preferences"]["models"] += app_dict["dynamic_preferences_users"]["models"]
            app_list.remove(app_dict["dynamic_preferences_users"])

        # Merge inventory
        if "inventory" in app_dict and "boardgames" in app_dict and "roleplaying" in app_dict:
            app_dict["inventory"]["models"] += app_dict["boardgames"]["models"]
            app_dict["inventory"]["models"] += app_dict["roleplaying"]["models"]
            app_list.remove(app_dict["boardgames"])
            app_list.remove(app_dict["roleplaying"])

        return app_list
