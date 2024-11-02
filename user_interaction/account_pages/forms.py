from django.forms import ModelForm
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "email"]
        labels = {
            "first_name": "Real Name",
        }
        help_texts = {
            "first_name": "This name is not connected to the name registered on your membership. Once membership is linked, the site will use the name registered on your membership instead.",
        }
