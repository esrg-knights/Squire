import json
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http.response import JsonResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import MarkdownImage
from core.tests.util import suppress_warnings

import shutil

User = get_user_model()

TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'test', 'output', 'media', 'martorupload')

###########################################################
# Tests usage of API functionality
###########################################################

@override_settings(MARKDOWN_IMAGE_MODELS=['core.markdownimage'], MEDIA_ROOT=TEST_MEDIA_ROOT)
class MartorImageUploadTest(TestCase):
    """
        Tests related to uploading images using Martor's Markdown widget
    """
    @classmethod
    def tearDownClass(cls):
        # Clean up after ourselves; we don't want our test images to keep existing
        #   each time we run our tests.
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create(username="test_user")
        self.upload_permission = Permission.objects.get(codename='can_upload_martor_images')
        self.user.user_permissions.add(self.upload_permission)
        self.client.force_login(self.user)

        self.content_type = ContentType.objects.get_for_model(MarkdownImage)

        self.valid_filename = os.path.join(settings.BASE_DIR, 'test', 'input', 'images', 'valid_image.png')
        self.invalid_filename = os.path.join(settings.BASE_DIR, 'test', 'input', 'images', 'not_an_image.png')

        self.martor_image_upload_url = reverse('core:martor_image_upload')

    def _test_image_upload(self, filename, expected_status_code=200,
            expected_json_error_message=None, content_type_id=None, object_id=None):
        """ General test structure for file uploads using the Martor editor """
        with open(filename, 'rb') as fp:
            if content_type_id is None:
                content_type_id = self.content_type.id

            # Set up POST data
            data = {
                'martor_image_upload_content_type_id': content_type_id,
                'markdown-image-upload': fp
            }
            if object_id is not None:
                data.update(martor_image_upload_object_id=object_id)

            # Make the request
            response = self.client.post(self.martor_image_upload_url, data)

        # Check response code
        self.assertEqual(response.status_code, expected_status_code)
        if expected_json_error_message is not None:
            self._test_invalid_json_response(response, message=expected_json_error_message)
        return response

    def _test_invalid_json_response(self, response, message=None):
        self.assertIsInstance(response, JsonResponse)

        if message is not None:
            try:
                resp_dict = json.loads(response.content)
            except ValueError:
                self.fail("Response did not contain valid JSON.")
            self.assertIn('error', resp_dict)
            self.assertIn(message, resp_dict['error'])

    def test_martor_settings_correct(self):
        """ Tests if the relevant URLs for Martor have been set up """
        self.assertEqual(reverse('core:martor_markdownify'), settings.MARTOR_MARKDOWNIFY_URL)
        self.assertEqual(self.martor_image_upload_url, settings.MARTOR_UPLOAD_URL)

    @suppress_warnings
    def test_upload_invalid_file_key(self):
        """ Tests if uploaded files must have a specific key in the POST data """
        with open(self.valid_filename, 'rb') as fp:
            response = self.client.post(self.martor_image_upload_url, {
                'foo': fp # Should be markdown-image-upload
            })
        self._test_invalid_json_response(response, message="Could not find an uploaded file")

    @suppress_warnings
    def test_upload_invalid_contenttype_object_id_combination(self):
        """ Tests if uploading bogus content_types or object_ids are caught """
        # Non-existent ContentType
        self._test_image_upload(self.valid_filename,
            content_type_id="I am a string",
            expected_status_code=400, expected_json_error_message="Invalid content_type/object_id combination"
        )

        # Non-existent object (bogus data)
        self._test_image_upload(self.valid_filename,
            object_id="I am a string",
            expected_status_code=400, expected_json_error_message="Invalid content_type/object_id combination"
        )

        # Non-existent object (valid number)
        self._test_image_upload(self.valid_filename,
            object_id=493,
            expected_status_code=400, expected_json_error_message="Invalid content_type/object_id combination"
        )

    @suppress_warnings
    def test_upload_invalid_content_type(self):
        """ Tests if images can only be uploaded for models specified in the settings """
        # Cannot upload MarkdownImages for Users
        self._test_image_upload(self.valid_filename,
            content_type_id=ContentType.objects.get_for_model(User).id,
            expected_status_code=400, expected_json_error_message="Cannot upload MarkdownImages for this model"
        )

    @suppress_warnings
    @override_settings(MAX_IMAGE_UPLOAD_SIZE=0)
    def test_upload_max_filesize(self):
        """ Tests if uploaded images cannot exceed the max file size """
        self._test_image_upload(self.valid_filename,
            expected_status_code=400, expected_json_error_message="Maximum image file size is"
        )

    @suppress_warnings
    def test_upload_invalid_image(self):
        """ Tests if uploading a file that is not an image raises a 400 Bad Request """
        self._test_image_upload(self.invalid_filename,
            expected_status_code=400, expected_json_error_message="Bad image format"
        )

    @suppress_warnings
    def test_upload_anonymous_user(self):
        """ Tests if anonymous users cannot upload images """
        self.client.logout()
        self._test_image_upload(self.valid_filename,
            expected_status_code=403
        )

    @suppress_warnings
    def test_upload_no_permission(self):
        """ Tests if the user does not have permissions to upload images """
        self.user.user_permissions.clear()
        self._test_image_upload(self.valid_filename,
            expected_status_code=403
        )

    def test_upload_valid(self):
        """ Tests if images can be uploaded when all parameters are valid """
        # Upload without an object_id
        self._test_image_upload(self.valid_filename)
        new_img = MarkdownImage.objects.filter(uploader=self.user, content_type=self.content_type, object_id=None).first()
        self.assertIsNotNone(new_img)

        # Upload with an object_id (attach it to the previously uploaded image)
        self._test_image_upload(self.valid_filename, object_id=new_img.id)
        related_img = MarkdownImage.objects.filter(uploader=self.user,
            content_type=self.content_type, object_id=new_img.id).first()
        self.assertIsNotNone(related_img)




