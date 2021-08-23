from django.db import models
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.text import slugify


from inventory.models import Item
from roleplaying.models import *
from roleplaying.models import get_system_image_upload_path, get_roleplay_item_file_upload_path


class TestRoleplayingSystem(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']

    def test_normal(self):
        system = RoleplayingSystem(
            name='test-name',
            short_description='short-test',
            long_description='some long text description test',
            image=None,
            is_public=True,
            rate_complexity=4,
            player_count='3-9',
            dice="5 d6's",
        )
        try:
            system.clean()
        except ValidationError as e:
            raise AssertionError(f"System object was not valid: {e}")

    def test_fields(self):
        # Test image field
        field = RoleplayingSystem._meta.get_field("image")
        self.assertIsInstance(field, models.ImageField)

        # Test choice field
        field = RoleplayingSystem._meta.get_field("rate_complexity")
        self.assertTrue(hasattr(field, 'choices'))
        self.assertTrue(len(field.choices), 5)

    def test_system_upload_path(self):
        system = RoleplayingSystem.objects.get(id=1)
        str_expected_upload_path = "images/roleplaying/system/{system_name}.png"
        system_name = f'{system.id}-{slugify(system.name)}'

        str_expected_upload_path = str_expected_upload_path.format(
            system_name=system_name
        )
        str_actual_upload_path = get_system_image_upload_path(system, "some_file_name.png")
        self.assertEqual(str_expected_upload_path, str_actual_upload_path)


class TestRoleplayingItem(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']

    def setUp(self):
        self.system = RoleplayingSystem.objects.create(
            name='test system',
            short_description='a short test description',
        )

    def test_fields(self):
        self.assertTrue(issubclass(RoleplayingItem, Item))

        # Test system field
        field = RoleplayingItem._meta.get_field("system")
        self.assertIsInstance(field, models.ForeignKey)

        # Test digital_version field
        field = RoleplayingItem._meta.get_field("local_file")
        self.assertIsInstance(field, models.FileField)

    def test_non_duplicate_location(self):
        """ Tests that an external file location and a local file can't both be set. """
        item = RoleplayingItem(external_file_url = "https://www.google.com")
        # Set a file location. Cleaning does not actually verify file existence so setting a name is enough to
        # imitate a linked file
        item.local_file.name = "test_file_location.txt"

        with self.assertRaises(ValidationError) as error:
            item.clean()
        self.assertEqual(error.exception.code, 'duplicate_location')

    def test_local_file_upload_path(self):
        # Basic upload path
        str_expected_upload_path = "local_only/files/item/roleplay/{filename}.png"

        # Check it for an item connected to a system
        instance = RoleplayingItem.objects.get(id=1)
        new_expected_upload_path = str_expected_upload_path.format(
            filename=f'{instance.system.id}-{instance.id}-{slugify(instance.name)}'
        )
        str_actual_upload_path = get_roleplay_item_file_upload_path(instance, "some_file_name.png")
        self.assertEqual(new_expected_upload_path, str_actual_upload_path)

        # Test it for items not connected to a system
        instance = RoleplayingItem.objects.get(id=5)
        new_expected_upload_path = str_expected_upload_path.format(
            filename=f'None-{instance.id}-{slugify(instance.name)}'
        )

        str_actual_upload_path = get_roleplay_item_file_upload_path(instance, "some_file_name.png")
        self.assertEqual(new_expected_upload_path, str_actual_upload_path)
