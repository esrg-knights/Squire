from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.test.utils import override_settings

from core.models import MarkdownImage, PresetImage, get_image_upload_path

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

    @override_settings(AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",))
    def test_get_images_for_user(self):
        user = User.objects.create_user(username="user", password="password")
        public_image = PresetImage.objects.create(name="public-image", image="", selectable=True)
        non_selectable_image = PresetImage.objects.create(name="non-public-image", image="", selectable=False)

        # User only has permission to choose selectable presetImages
        images = set(PresetImage.objects.for_user(user))
        self.assertSetEqual(images, {public_image})

        # User can select all presetImages with the right permissions
        user.user_permissions.add(Permission.objects.get(codename="can_select_presetimage_any"))
        # Re-fetch user from database because of permission caching
        user = User.objects.get(username=user)
        images = set(PresetImage.objects.for_user(user))
        self.assertSetEqual(images, {public_image, non_selectable_image})


@override_settings(MARKDOWN_IMAGE_MODELS=["core.markdownimage"])
class MarkdownImageTest(TestCase):
    """
    Tests related to the MarkdownImage class
    """

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(MarkdownImage)

    def test_clean_invalid_content_type(self):
        """Tests if objects cannot be created for ContentTypes not in the settings"""
        # Cannot create MarkdownImages for Users
        md_img = MarkdownImage(content_type=ContentType.objects.get_for_model(User))
        with self.assertRaisesMessage(ValidationError, "MarkdownImages cannot be uploaded for this ContentType"):
            md_img.clean()

    def test_clean_invalid_content_object(self):
        """Tests if invalid ContentType-Object_id combinations are not allowed"""
        md_img = MarkdownImage(content_type=self.content_type, object_id=1234)
        with self.assertRaisesMessage(
            ValidationError, "The selected ContentType does not have an object with this id"
        ):
            md_img.clean()

    def test_clean_ok(self):
        """Tests if the clean method passes if everything is valid"""
        rel_obj = MarkdownImage.objects.create(content_type=self.content_type)
        md_img = MarkdownImage(content_type=self.content_type, object_id=rel_obj.id)
        md_img.clean()
