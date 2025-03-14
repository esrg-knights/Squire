from django.apps import AppConfig


class GsuiteIntergrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gsuite_intergration"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Gsuite connection
        self.Gsuite_client = None


