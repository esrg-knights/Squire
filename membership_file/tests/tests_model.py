from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase

from membership_file.models import Member, MemberLog, MemberLogField, Room, MemberYear, Membership


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

    def test_is_considered_member_active_years(self):
        """ Tests member.is_considered_member when active years are present """
        self.assertTrue(Member.objects.get(id=1).is_considered_member())
        self.assertFalse(Member.objects.get(id=2).is_considered_member())
        # Member is deregistered so should not be member, even though there is an active membership connected
        # (why this scenario would occur in real life I don't know, but let's set consistent behavior)
        self.assertFalse(Member.objects.get(id=3).is_considered_member())

    def test_is_considered_member_no_active_years(self):
        MemberYear.objects.update(is_active=False)
        self.assertTrue(Member.objects.get(id=1).is_considered_member())
        self.assertTrue(Member.objects.get(id=2).is_considered_member())
        # Member is deregistered so should not be member, even though there is an active membership connected
        # (why this scenario would occur in real life I don't know, but let's set consistent behavior)
        self.assertFalse(Member.objects.get(id=3).is_considered_member())


# Tests methods related to the Room model
class RoomModelTest(TestCase):
    # Tests the display method of Room
    def test_room_display(self):
        room = Room(id=2, name='Basement', access='Keycard')
        self.assertEqual(str(room), "Basement (Keycard)")


class MemberYearTest(TestCase):
    fixtures = ['test_users', 'test_members']

    def test_memberyear(self):
        year = MemberYear.objects.get(id=1)
        self.assertEqual(str(year), "ActiveYear")


class MembershipTest(TestCase):
    fixtures = ['test_users', 'test_members']

    def test_unique_together(self):
        """ Tests the unique together property for member and year """
        self.assertTrue(Membership.objects.filter(year_id=1, member_id=1).exists())
        with self.assertRaises(IntegrityError):
            Membership.objects.create(year_id=1, member_id=1)
