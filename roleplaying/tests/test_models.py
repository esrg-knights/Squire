from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.text import slugify


from membership_file.models import Member
from inventory.models import Item, BoardGame, Ownership, valid_item_class_ids, ItemManager, \
    get_item_image_upload_path, MiscellaneousItem
from roleplaying.models import *


class TestRoleplayingSystem(TestCase):
    def test_normal(self):
        system = RoleplayingSystem(
            name='test-name',
            short_description='short-test',
            long_description='some long text description test',
            image=None,
            is_live=True,
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


class TestRoleplayingItem(TestCase):

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
        field = RoleplayingItem._meta.get_field("digital_version")
        self.assertIsInstance(field, models.FileField)
