from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase

from membership_file.models import Member, MemberLog, MemberLogField, MemberManager, Room, MemberYear, Membership


##################################################################################
# Test the Member model's methods
# @since 16 MAR 2020
##################################################################################


class MemberManagerTest(TestCase):
    """Tests related to the MemberManager"""

    def setUp(self):
        # Members with active membership
        self._active = Member.objects.create(
            first_name="Foo", last_name="Oof", legal_name="Foo Oof", email="foo@example.com"
        )
        self._deregistered = Member.objects.create(
            is_deregistered=True, first_name="Bar", last_name="Rab", legal_name="Bar Rab", email="bar@example.com"
        )
        self._pending_deletion = Member.objects.create(
            marked_for_deletion=True, first_name="Baz", last_name="Zab", legal_name="Baz Zab", email="baz@example.com"
        )
        self._honorary = Member.objects.create(
            first_name="Ya", last_name="Ay", legal_name="Ya Ay", email="ay@example.com", is_honorary_member=True
        )

        year = MemberYear.objects.create(name="1970", is_active=True)
        year.members.set([self._active, self._deregistered, self._pending_deletion])
        year.save()

        # Members without active membership
        self._inactive = Member.objects.create(
            first_name="iFoo", last_name="Oof", legal_name="iFoo Oof", email="ifoo@example.com"
        )
        self._inactive_deregistered = Member.objects.create(
            is_deregistered=True, first_name="iBar", last_name="iRab", legal_name="Bar Rab", email="ibar@example.com"
        )
        self._inactive_pending_deletion = Member.objects.create(
            marked_for_deletion=True,
            first_name="iBaz",
            last_name="iZab",
            legal_name="Baz Zab",
            email="ibaz@example.com",
        )

    def test_filter_active_no_active_year(self):
        """Tests if filter_active() returns all members that aren't deregistered and
        marked for deletion when there are no active years
        """
        MemberYear.objects.update(is_active=False)

        active_members = Member.objects.filter_active()
        self.assertIn(self._active, active_members)
        self.assertIn(self._inactive, active_members)
        self.assertIn(self._honorary, active_members)
        self.assertEqual(len(active_members), 3)

    def test_filter_active_active_year(self):
        """Tests if filter_active() returns all members that aren't deregistered and
        marked for deletion only in active years
        """
        active_members = Member.objects.filter_active()
        self.assertIn(self._active, active_members)
        self.assertNotIn(self._inactive, active_members)
        self.assertIn(self._honorary, active_members)
        self.assertEqual(len(active_members), 2)

    def test_filter_active_duplicates(self):
        """Tests if filter_active() accounts for duplicates when multiple years are active simultaneously"""
        year = MemberYear.objects.create(name="1980", is_active=True)
        year.members.set([self._active, self._deregistered, self._pending_deletion])

        active_members = Member.objects.filter_active()
        self.assertIn(self._active, active_members)
        self.assertNotIn(self._inactive, active_members)
        self.assertIn(self._honorary, active_members)
        self.assertEqual(len(active_members), 2)


# Tests methods related to the Member model
class MemberModelTest(TestCase):
    fixtures = ["test_users.json", "test_members.json"]

    # Tests the display method of the MemberLog
    def test_memberlog_display(self):
        memberlog = MemberLog(id=1, user=User.objects.first(), member=Member.objects.first(), log_type="UPDATE")
        self.assertEqual(
            str(memberlog),
            f"[UPDATE] {str(User.objects.first())} updated {str(Member.objects.first())}'s information (1)",
        )

    # Tests the display method of the MemberLogField
    def test_memberlogfield_display(self):
        memberlogfield = MemberLogField(id=2, field="name", old_value="Bob", new_value="Charlie")
        self.assertEqual(str(memberlogfield), f"name was updated: <Bob> -> <Charlie> (2)")

    def test_is_active_active_years(self):
        """Tests member.is_active when active years are present"""
        self.assertTrue(Member.objects.get(id=1).is_active)
        self.assertFalse(Member.objects.get(id=2).is_active)
        # Member is deregistered so should not be member, even though there is an active membership connected
        # (why this scenario would occur in real life I don't know, but let's set consistent behavior)
        self.assertFalse(Member.objects.get(id=3).is_active)

        # Honorary members are always active
        honorary = Member.objects.create(
            first_name="John", last_name="Doe", legal_name="JD", email="johndoe@example.com", is_honorary_member=True
        )
        self.assertTrue(honorary.is_active)
        # unless they're actively deregistered
        honorary.is_deregistered = True
        self.assertFalse(honorary.is_active)

    def test_is_active_no_active_years(self):
        MemberYear.objects.update(is_active=False)
        self.assertTrue(Member.objects.get(id=1).is_active)
        self.assertTrue(Member.objects.get(id=2).is_active)
        # Member is deregistered so should not be member, even though there is an active membership connected
        # (why this scenario would occur in real life I don't know, but let's set consistent behavior)
        self.assertFalse(Member.objects.get(id=3).is_active)

        # Honorary members are always active
        honorary = Member.objects.create(
            first_name="John", last_name="Doe", legal_name="JD", email="johndoe@example.com", is_honorary_member=True
        )
        self.assertTrue(honorary.is_active)
        # unless they're actively deregistered
        honorary.is_deregistered = True
        self.assertFalse(honorary.is_active)


# Tests methods related to the Room model
class RoomModelTest(TestCase):
    # Tests the display method of Room
    def test_room_display(self):
        room = Room(id=2, name="Basement", access_type=Room.ACCESS_OTHER, access_specification="Keycard")
        self.assertEqual(str(room), "Basement (Other - Keycard)")

        room = Room(id=2, name="Basement", access_type=Room.ACCESS_KEY, room_number="1.042")
        self.assertEqual(str(room), "1.042 - Basement (Key)")


class MemberYearTest(TestCase):
    fixtures = ["test_users", "test_members"]

    def test_memberyear(self):
        year = MemberYear.objects.get(id=1)
        self.assertEqual(str(year), "ActiveYear")


class MembershipTest(TestCase):
    fixtures = ["test_users", "test_members"]

    def test_unique_together(self):
        """Tests the unique together property for member and year"""
        self.assertTrue(Membership.objects.filter(year_id=1, member_id=1).exists())
        with self.assertRaises(IntegrityError):
            Membership.objects.create(year_id=1, member_id=1)

    def test_str(self):
        """Tests __str__ of Membership"""
        # Member linked
        membership = Membership.objects.get(year_id=1, member_id=1)
        self.assertEqual(str(membership), "Charlie van der Dommel for ActiveYear")

        # No member linked
        membership = Membership.objects.create(year_id=1, member=None)
        self.assertEqual(str(membership), "Deleted member for ActiveYear")
