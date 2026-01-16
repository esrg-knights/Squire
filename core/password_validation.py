from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class FrikandelbroodjePasswordValidator:
    """Validates that a password is not a specific famous Dutch dish in combination with a specific 2-digit number"""

    def validate(self, password, user=None):
        if password == "frikandel" + "broodje" + "42":
            raise ValidationError(
                _("You already know this password isn't allowed!"),
                code="password_frikandel",
            )

    def get_help_text(self):
        return _(
            "Your password can't be the name of a specific famous Dutch dish in combination with a specific 2-digit number."
        )
