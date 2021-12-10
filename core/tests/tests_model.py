import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, override_settings
from django.test.testcases import SimpleTestCase
from django.test.utils import isolate_apps, override_settings
from django.utils import timezone
from unittest.mock import patch

from core.models import (MarkdownImage, PresetImage,
                         get_image_upload_path)
from core.pins import Pin, PinManager, PinnableMixin

User = get_user_model()

##################################################################################
# Test cases for the models in core
# @since 16 MAR 2020
##################################################################################

class PresetImageTest(TestCase):
    # Tests if the preset images are uploaded to the correct location
    def test_image_upload_path(self):
        presetimage = PresetImage(id=1, name="na.me with / weird characters %", image="")
        str_expected_upload_path = "images/presets/name-with-weird-characters.png"
        str_actual_upload_path = get_image_upload_path(presetimage, "filename.png")
        self.assertEqual(str_expected_upload_path, str_actual_upload_path)

    @override_settings(AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',))
    def test_get_images_for_user(self):
        user = User.objects.create_user(username='user', password='password')
        public_image = PresetImage.objects.create(name="public-image", image="", selectable=True)
        non_selectable_image = PresetImage.objects.create(name="non-public-image", image="", selectable=False)

        # User only has permission to choose selectable presetImages
        images = set(PresetImage.objects.for_user(user))
        self.assertSetEqual(images, {public_image})

        # User can select all presetImages with the right permissions
        user.user_permissions.add(Permission.objects.get(codename='can_select_presetimage_any'))
        # Re-fetch user from database because of permission caching
        user = User.objects.get(username=user)
        images = set(PresetImage.objects.for_user(user))
        self.assertSetEqual(images, {public_image, non_selectable_image})


@override_settings(MARKDOWN_IMAGE_MODELS=['core.markdownimage'])
class MarkdownImageTest(TestCase):
    """
        Tests related to the MarkdownImage class
    """

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(MarkdownImage)

    def test_clean_invalid_content_type(self):
        """ Tests if objects cannot be created for ContentTypes not in the settings """
        # Cannot create MarkdownImages for Users
        md_img = MarkdownImage(content_type=ContentType.objects.get_for_model(User))
        with self.assertRaisesMessage(ValidationError,
                "MarkdownImages cannot be uploaded for this ContentType"):
            md_img.clean()

    def test_clean_invalid_content_object(self):
        """ Tests if invalid ContentType-Object_id combinations are not allowed """
        md_img = MarkdownImage(content_type=self.content_type, object_id=1234)
        with self.assertRaisesMessage(ValidationError,
                "The selected ContentType does not have an object with this id"):
            md_img.clean()

    def test_clean_ok(self):
        """ Tests if the clean method passes if everything is valid """
        rel_obj = MarkdownImage.objects.create(content_type=self.content_type)
        md_img = MarkdownImage(content_type=self.content_type, object_id=rel_obj.id)
        md_img.clean()


def mock_now(dt=None):
    """ Script that changes the default now time to a preset value """
    if dt is None:
        dt = datetime.datetime(2020, 8, 11, 0, 0)

    def adjust_now_time():
        return timezone.make_aware(dt)

    return adjust_now_time


from roleplaying.models import RoleplayingSystem
class TestPinnableModel(RoleplayingSystem):
    """
        A proxy model used to
    """
    class Meta:
        proxy = True




@isolate_apps('core', attr_name='apps')
class PinManagerTest(TestCase):
    """
        Tests related to the PinManager
    """
    fixtures = ['test_pins.json', 'test_users.json']


    def mock_now():
        return datetime.datetime(year=2021, month=1, day=1, hour=20, tzinfo=timezone.utc)

    def setUp(self):
        self.pin_1: Pin = Pin.objects.get(id=1)
        self.pin_2: Pin = Pin.objects.get(id=2)

        self.object = PresetImage.objects.get(id=1)
        self.content_type = ContentType.objects.get_for_model(self.object)
        self.user = User.objects.get(username='test_user')

        self.pinmanager = PinManager()

        # Create a model that we can pin
        class PinnablePresetImage(PinnableMixin, PresetImage):
            """
                A wrapper for PresetImages that allows it to be pinned.
                Note that the `pins` attribute of this model is unavailable
                using this setup.
                We're linking it to PresetImage as that is an existing model,
                allowing us to save model instances. We're using a model from
                the `core` app on purpose here, but ideally we'd create an
                entirely new one just for testing.

                TODO: Adding specific test-models in Django sucks; there has to
                be a better way...

                Current Setup:
                https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/#isolating-model-registration

            """
            class Meta:
                proxy = True

            def get_pin_description(self, pin):
                return "REEEEEEEEEE"

        self.pinnable_model = self.apps.get_model('core', 'PinnablePresetImage')
        self.assertIs(self.pinnable_model, PinnablePresetImage) # Sanity check

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_queryset_used(self, mock_now):
        """ Tests if an alternative queryset is used if it is passed as a parameter """
        queryset = Pin.objects.filter(id=1)
        pins = self.pinmanager.for_user(user=self.user, queryset=queryset)

        # Only a single pin should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertEqual(len(pins), 1)

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_all_pins(self, mock_now):
        """ Tests if pins are visible if they are published, not expired, and not members-only """
        pins = self.pinmanager.for_user(user=self.user)

        # All pins should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertIn(self.pin_2, pins)
        self.assertEqual(len(pins), 2)

    def _test_pin2_only_accessible_with_perm(self, perms, pin_2_kwargs):
        """
            Tests if `self.pin_2` is only accessible for users with the given
            permission(s), and that `self.pin_1` is always accessible regardless
            of permissions.
        """
        # Update the pin with the new values
        Pin.objects.filter(id=self.pin_2.id).update(**pin_2_kwargs)

        # Pin 2 is not accessible without the permission
        pins = self.pinmanager.for_user(user=self.user)

        # All pins should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertNotIn(self.pin_2, pins)
        self.assertEqual(len(pins), 1)

        # Pin 2 is accessible with the permission
        self.user.user_permissions.add(perms)
        self.user = User.objects.get(id=self.user.id) # Force the permission cache to reload
        pins = self.pinmanager.for_user(user=self.user)

        self.assertIn(self.pin_1, pins)
        self.assertIn(self.pin_2, pins)
        self.assertEqual(len(pins), 2)


    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_members_only(self, mock_now):
        """ Tests if pins are visible if they are members-only and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_members_only_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'is_members_only': True
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_not_published(self, mock_now):
        """ Tests if pins are visible if they are not published and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_future_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_publish_date': None
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_future_publish(self, mock_now):
        """ Tests if pins are visible if they publish in the future and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_future_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_publish_date': datetime.datetime(year=2022, month=1, day=1, tzinfo=timezone.utc)
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_past_expiry(self, mock_now):
        """ Tests if pins are visible if they are expired and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_expired_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_expiry_date': datetime.datetime(year=1970, month=1, day=1, tzinfo=timezone.utc)
        })


