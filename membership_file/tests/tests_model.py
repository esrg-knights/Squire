from django.test import TestCase

from membership_file.models import Member, get_member_display_name, MemberLog, MemberLogField
from membership_file.models import MemberUser as User


##################################################################################
# Test the Member model's methods
# @since 16 MAR 2020
##################################################################################


# Tests methods related to the Member model
class MemberModelTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    # Tests whether a member is displayed correctly
    def test_member_display_method(self):
        # Member has the correct display method
        user = User.objects.filter(username="test_user").first()
        display_str = get_member_display_name(user)
        self.assertEqual(display_str, Member.objects.filter(user__username="test_user").first().get_full_name())

        # Non-Member has the correct display method
        user = User.objects.filter(username="test_user_alt").first()
        display_str = get_member_display_name(user)
        self.assertEqual(display_str, user.get_simple_display_name())

    # Tests the display method of the MemberLog
    def test_memberlog_display(self):
        memberlog = MemberLog(id=1, user=User.objects.first(), member=Member.objects.first(), log_type="UPDATE")
        self.assertEqual(str(memberlog), f"[UPDATE] {str(User.objects.first())} updated {str(Member.objects.first())}'s information (1)")

    # Tests the display method of the MemberLogField
    def test_memberlogfield_display(self):
        memberlogfield = MemberLogField(id=2, field="name", old_value="Bob", new_value="Charlie")
        self.assertEqual(str(memberlogfield), f"name was updated: <Bob> -> <Charlie> (2)")
