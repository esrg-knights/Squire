from django.core.exceptions import ValidationError
from django.test import TestCase


from inventory.models import Item, BoardGame, Ownership, valid_item_class_ids


class ModelRelationTest(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']


    def test_ownership_validation(self):
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

    def test_valid_item_class_ids(self):
        """ Tests the method to return the right class ids """
        # I'm cheating a bit here by checking the amount of classes found as valid. It's not likely to mess this up
        # I do check that it is a dict with the right search key that is returned
        valid_ids = valid_item_class_ids()
        self.assertEqual(len(valid_ids.keys()), 1)
        self.assertIn('id__in', valid_ids.keys())

        # There is only 1 item implemented: Boardgame
        self.assertEqual(len(valid_ids['id__in']), 1)

    def test_ownership_count(self):
        """ Test the ownership link from the item side. Tested on boardgame item """
        self.assertEqual(3, BoardGame.objects.get(id=1).ownerships.count())
        # Currently in possession also checks for is_active
        self.assertEqual(2, BoardGame.objects.get(id=1).currently_in_possession().count())
        self.assertEqual(1, BoardGame.objects.get(id=2).currently_in_possession().count())
