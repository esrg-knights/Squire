from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test.utils import override_settings

from core.models import ExtendedUser, get_image_upload_path, PresetImage

User = get_user_model()

##################################################################################
# Test cases for the models in core
# @since 16 MAR 2020
##################################################################################

# Tests for ExtendedUser
class ExtendedUserTest(TestCase):
    def setUp(self):
        self.user = ExtendedUser(username='the_rock', password='password',
            first_name='Dwayne', last_name='Johnson', email='test@example.com')
    
    # Tests the get_simple_display_name method
    def test_get_simple_display_name(self):
        user = ExtendedUser(username='blurp', password='password')
        self.assertEqual(user.get_simple_display_name(), "blurp")

        self.assertEqual(self.user.get_simple_display_name(), "Dwayne")

    # Tests the getter and setter of the application-wide display name of users
    def test_get_set_display_name(self):
        self.assertEqual(self.user.get_display_name(), self.user.get_simple_display_name())

        ExtendedUser.set_display_name_method(lambda x: f"{x.first_name} 'the Rock' {x.last_name}")
        self.assertEqual(self.user.get_display_name(), "Dwayne 'the Rock' Johnson")


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
