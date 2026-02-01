from django.apps import AppConfig


class CommitteesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "committees"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.email_manager = None

    def ready(self):
        from committees.email import SquireEmailManager

        self.email_manager = SquireEmailManager()
        if not self.email_manager.is_valid:
            self.email_manager = None
