from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.text import slugify


from membership_file.models import Member
from inventory.models import Item, Ownership, valid_item_class_ids, ItemManager,\
    get_item_image_upload_path, MiscellaneousItem


class TestOwnership(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def test_ownership_owner_validation(self):
        """ Test the custom clean criteria related to member/group """
        misc_item = MiscellaneousItem.objects.first()
        ownership = Ownership(
            content_object = misc_item
        )

        # Either member or group needs to be defined
        with self.assertRaises(ValidationError) as error:
            ownership.clean()
        self.assertEqual(error.exception.code, 'required')

        # Member and group can't both be defined
        ownership = Ownership(
            # content_object = MiscellaneousItem,
            added_by_id=2,
            member_id = 2,
            group_id = 1,
            content_type_id=ContentType.objects.get_for_model(MiscellaneousItem).id,
            object_id = misc_item.id,
        )
        with self.assertRaises(ValidationError) as error:
            ownership.full_clean()
        error_dict = error.exception.error_dict
        error = error_dict['__all__'][0]
        self.assertEqual(error.code, 'invalid')

    def test_ownership_item_validation(self):
        ownership = Ownership(
            member_id = 2,
            added_by_id=2,
            content_type_id=ContentType.objects.get_for_model(MiscellaneousItem).id,
            object_id = 999,
        )
        with self.assertRaises(ValidationError) as error:
            ownership.full_clean()
        error_dict = error.exception.error_dict
        error = error_dict['__all__'][0]
        self.assertEqual(error.code, 'item_nonexistent')

    def test_valid_item_class_ids(self):
        """ Tests the method to return the right class ids """
        # I'm cheating a bit here by checking the amount of classes found as valid. It's not likely to mess this up
        # I do check that it is a dict with the right search key that is returned
        valid_ids = valid_item_class_ids()
        self.assertEqual(len(valid_ids.keys()), 1)
        self.assertIn('id__in', valid_ids.keys())

        # There is only 1 item implemented: MiscellaneousItem
        self.assertEqual(len(valid_ids['id__in']), len(Item.get_item_contenttypes()))

    def test_owner(self):
        self.assertEqual(Ownership.objects.get(id=1).owner, Member.objects.get(id=1))
        self.assertEqual(Ownership.objects.get(id=3).owner, Group.objects.get(id=2))

    def test_str(self):
        ownership = Ownership.objects.filter(member__isnull=False).first()
        self.assertEqual(ownership.__str__(), f'{ownership.content_object} supplied by {ownership.member}')

        ownership = Ownership.objects.filter(group__isnull=False).first()
        self.assertEqual(ownership.__str__(), f'{ownership.content_object} owned ({ownership.group})')


class TestItem(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    # Tests if the item images are uploaded to the correct location
    def test_item_upload_path(self):
        item = MiscellaneousItem.objects.get(id=1)
        str_expected_upload_path = "images/item/{type_str}/{item_id}.png"

        str_expected_upload_path = str_expected_upload_path.format(
            item_id=f'{item.id}-{slugify(item.name)}',
            type_str=slugify(item.__class__.__name__),
        )
        str_actual_upload_path = get_item_image_upload_path(item, "some_file_name.png")
        self.assertEqual(str_expected_upload_path, str_actual_upload_path)

    def test_get_item_contenttypes(self):
        item_contenttypes = Item.get_item_contenttypes()
        self.assertEqual(len(item_contenttypes), len(Item.__subclasses__()))

        self.assertIn(ContentType.objects.get_for_model(MiscellaneousItem), item_contenttypes)
        self.assertIn(ContentType.objects.get_for_model(MiscellaneousItem), item_contenttypes)

    def test_ownerships_relation(self):
        # We use MiscellaneousItems as a proxy
        self.assertEqual(3, MiscellaneousItem.objects.get(id=1).ownerships.count())

    def test_currently_in_possession(self):
        """ Test the ownership link from the item side. Tested on MiscellaneousItem item """
        # We use MiscellaneousItems as a proxy
        self.assertEqual(2, MiscellaneousItem.objects.get(id=1).currently_in_possession().count())
        self.assertEqual(1, MiscellaneousItem.objects.get(id=2).currently_in_possession().count())
        self.assertEqual(0, MiscellaneousItem.objects.get(id=4).currently_in_possession().count())

    def test_is_owned_by_association(self):
        """ Test the check if the item is owned by the association """
        self.assertTrue(MiscellaneousItem.objects.get(id=1).is_owned_by_association())
        # There is an ownership, but it is not active
        self.assertFalse(MiscellaneousItem.objects.get(id=4).is_owned_by_association())

    def test_is_loaned_by_member(self):
        """ Checks if there is an active instance of this item at the Knights owned by a member """
        self.assertTrue(MiscellaneousItem.objects.get(id=1).is_loaned_by_member())
        self.assertFalse(MiscellaneousItem.objects.get(id=2).is_loaned_by_member())

    def test_other_fields(self):
        # This method has no effects in this module, so returns an empty list
        # Its further tested in boardgames
        self.assertEqual(MiscellaneousItem.objects.get(id=1).other_fields(), [])

    def test_objects_manager(self):
        self.assertIsInstance(MiscellaneousItem.objects, ItemManager)


class TestItemManager(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def setUp(self):
        self.manager = ItemManager()
        self.manager.model = MiscellaneousItem

    def test_get_all_in_possession(self):
        self.assertEqual(2, self.manager.get_all_in_possession().count())
        Ownership.objects.filter(id=3).update(is_active=False)
        self.assertEqual(2, self.manager.get_all_in_possession().count())

    def test_get_all_owned(self):
        self.assertEqual(2, self.manager.get_all_owned().count())
        Ownership.objects.filter(id=3).update(is_active=False)
        self.assertEqual(1, self.manager.get_all_owned().count())\

    def test_get_all_owned_by(self):
        member = Member.objects.get(id=1)
        self.assertEqual(1, self.manager.get_all_owned_by(member=member).count())
        member = Member.objects.get(id=2)
        self.assertEqual(0, self.manager.get_all_owned_by(member=member).count())

        group = Group.objects.get(id=1)
        self.assertEqual(0, self.manager.get_all_owned_by(group=group).count())
        group = Group.objects.get(id=2)
        self.assertEqual(2, self.manager.get_all_owned_by(group=group).count())
