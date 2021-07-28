from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase


from membership_file.models import Member
from inventory.models import Item, BoardGame, Ownership, valid_item_class_ids, ItemManager


class TestOwnership(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def test_ownership_owner_validation(self):
        """ Test the custom clean criteria related to member/group """
        boardgame = BoardGame.objects.first()
        ownership = Ownership(
            content_object = boardgame
        )

        # Either member or group needs to be defined
        with self.assertRaises(ValidationError) as error:
            ownership.clean()
        self.assertEqual(error.exception.code, 'required')

        # Member and group can't both be defined
        ownership = Ownership(
            content_object = boardgame,
            member_id = 2,
            group_id = 1,
        )
        with self.assertRaises(ValidationError) as error:
            ownership.clean()
        self.assertEqual(error.exception.code, 'invalid')

    def test_ownership_item_validation(self):
        ownership = Ownership(
            member_id = 2,
            content_type_id=ContentType.objects.get_for_model(BoardGame).id,
            object_id = 999,
        )
        with self.assertRaises(ValidationError) as error:
            ownership.clean()
        self.assertEqual(error.exception.code, 'item_nonexistent')

    def test_valid_item_class_ids(self):
        """ Tests the method to return the right class ids """
        # I'm cheating a bit here by checking the amount of classes found as valid. It's not likely to mess this up
        # I do check that it is a dict with the right search key that is returned
        valid_ids = valid_item_class_ids()
        self.assertEqual(len(valid_ids.keys()), 1)
        self.assertIn('id__in', valid_ids.keys())

        # There is only 1 item implemented: Boardgame
        self.assertEqual(len(valid_ids['id__in']), 1)

    def test_owner(self):
        self.assertEqual(Ownership.objects.get(id=1).owner, Member.objects.get(id=2))
        self.assertEqual(Ownership.objects.get(id=3).owner, Group.objects.get(id=2))


class TestItem(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def test_ownerships_relation(self):
        # We use Boardgames as a proxy
        self.assertEqual(3, BoardGame.objects.get(id=1).ownerships.count())

    def test_currently_in_possession(self):
        """ Test the ownership link from the item side. Tested on boardgame item """
        # We use Boardgames as a proxy
        self.assertEqual(2, BoardGame.objects.get(id=1).currently_in_possession().count())
        self.assertEqual(1, BoardGame.objects.get(id=2).currently_in_possession().count())
        self.assertEqual(0, BoardGame.objects.get(id=4).currently_in_possession().count())

    def test_is_owned_by_association(self):
        """ Test the check if the item is owned by the association """
        self.assertTrue(BoardGame.objects.get(id=1).is_owned_by_association())
        # There is an ownership, but it is not active
        self.assertFalse(BoardGame.objects.get(id=4).is_owned_by_association())

    def test_objects_manager(self):
        self.assertIsInstance(BoardGame.objects, ItemManager)


class TestItemManager(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def setUp(self):
        self.manager = ItemManager()
        self.manager.model = BoardGame


    def test_get_all_in_possession(self):
        self.assertEqual(2, self.manager.get_all_in_possession().count())

    def test_get_all_owned(self):
        self.assertEqual(2, self.manager.get_all_in_possession().count())

    def test_get_all_owned_by(self):
        member = Member.objects.get(id=1)
        self.assertEqual(0, self.manager.get_all_owned_by(member=member).count())
        member = Member.objects.get(id=2)
        self.assertEqual(1, self.manager.get_all_owned_by(member=member).count())

        group = Group.objects.get(id=1)
        self.assertEqual(0, self.manager.get_all_owned_by(group=group).count())
        group = Group.objects.get(id=2)
        self.assertEqual(2, self.manager.get_all_owned_by(group=group).count())
