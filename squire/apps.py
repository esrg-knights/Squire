from django.contrib.admin.apps import AdminConfig


class SquireAdminConfig(AdminConfig):
    default_site = "squire.admin.SquireAdminSite"
