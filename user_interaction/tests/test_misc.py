from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()

##################################################################################
# Tests for anything that cannot be categorised otherwise
# @since 21 NOV 2021
##################################################################################


class DisplayTest(TestCase):
    """
    Tests for displaying certain information in the frontend
    """

    fixtures = ["test_users.json", "test_members.json"]

    def test_user_display_method(self):
        """Test whether users are displayed correctly, depending on their membership status"""
        # If the user is a member, should display the member's name
        user = User.objects.filter(username="test_member").first()
        self.assertEqual(str(user), user.member.get_full_name())

        # Non-member without a first_name ("Real name") set should display the username
        user = User.objects.filter(username="test_user").first()
        user.first_name = "My Real Name"
        self.assertEqual(str(user), user.first_name)

        # Non-member WITH a first_name ("Real name") set should display its first_name
        user.first_name = None
        self.assertEqual(str(user), user.username)
