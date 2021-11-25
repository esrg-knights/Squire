from django.contrib.auth.models import User
from django.test import TestCase

from membership_file.models import Member, MemberLog, MemberLogField, Room


##################################################################################
# Test the Member model's methods
# @since 16 MAR 2020
##################################################################################


# Tests methods related to the Member model
class MemberModelTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    # Tests the display method of the MemberLog
    def test_memberlog_display(self):
        memberlog = MemberLog(id=1, user=User.objects.first(), member=Member.objects.first(), log_type="UPDATE")
        self.assertEqual(str(memberlog), f"[UPDATE] {str(User.objects.first())} updated {str(Member.objects.first())}'s information (1)")

    # Tests the display method of the MemberLogField
    def test_memberlogfield_display(self):
        memberlogfield = MemberLogField(id=2, field="name", old_value="Bob", new_value="Charlie")
        self.assertEqual(str(memberlogfield), f"name was updated: <Bob> -> <Charlie> (2)")


# Tests methods related to the Room model
class RoomModelTest(TestCase):
    # Tests the display method of Room
    def test_room_display(self):
        room = Room(id=2, name='Basement', access='Keycard')
        self.assertEqual(str(room), "Basement (Keycard)")
