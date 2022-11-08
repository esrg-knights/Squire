from django.test import TestCase

from unittest.mock import patch

from utils.testing import FormValidityMixin
from nextcloud_integration.forms import FileMoveForm, FolderCreateForm, SynchFileToFolderForm
from nextcloud_integration.models import NCFolder
from . import mock_ls, mock_exists


class FileMoveFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FileMoveForm

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('directory_name')
        self.assertHasField('file_name')

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient.ls', side_effect=mock_ls())
    def test_file_name_field(self, ls_mock):
        form = self.build_form(data={})
        name_field = form.fields['file_name']
        choices = [entry[0] for entry in name_field.choices]
        # See mock_ls for list of contents
        self.assertNotIn('documentation', choices)
        self.assertNotIn('documentation/', choices)
        self.assertIn('new_file.txt', choices)
        self.assertIn('icon_small.png', choices)

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient.ls', side_effect=mock_ls())
    def test_form_valid(self, ls_mock):
        self.assertFormValid(data={'file_name': 'new_file.txt', 'directory_name': 'NewFoldeer'})

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient.ls', side_effect=mock_ls())
    def test_directory_name_validation(self, ls_mock):
        self.assertFormHasError(
            data={'file_name': 'new_file.txt', 'directory_name': '/NewFoldeer'},
            code='invalid_directory_name'
        )


class FileMoveFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = SynchFileToFolderForm

    def setUp(self):
        self.folder = NCFolder.objects.first()
        super(FileMoveFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('folder', self.folder)
        return super(FileMoveFormTestCase, self).get_form_kwargs(**kwargs)

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('display_name')
        self.assertHasField('description')
        self.assertHasField('selected_file')

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient.ls', side_effect=mock_ls())
    def test_selected_file_field(self, ls_mock):
        form = self.build_form(data={})
        name_field = form.fields['selected_file']
        choices = [entry[0] for entry in name_field.choices]
        # See mock_ls for list of contents
        self.assertNotIn('documentation', choices)
        self.assertNotIn('documentation/', choices)
        self.assertIn('new_file.txt', choices)
        self.assertIn('icon_small.png', choices)

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient.ls', side_effect=mock_ls())
    def test_form_valid(self, ls_mock):
        form = self.assertFormValid(data={
            'display_name': 'New Folder',
            'description': "Test file that does not actually exist",
            'selected_file': 'new_file.txt',
        })
        self.assertEqual(form.instance.connection, "NcS")
        self.assertEqual(form.instance.folder, self.folder)
        self.assertEqual(form.instance.slug, "new-folder")
