from django.test import TestCase, override_settings
from django.forms import ModelForm

from utils.testing import FormValidityMixin

from nextcloud_integration.forms import (
    FileMoveForm,
    FolderCreateForm,
    SyncFileToFolderForm,
    FolderEditForm,
    FileEditForm,
    FileEditFormset,
    FolderEditFormGroup,
)
from nextcloud_integration.models import SquireNextCloudFolder, SquireNextCloudFile
from . import *


# Note about the patch, make sure to select the nextcloud client constructor from forms as that is loaded before the
# method is adjusted. As such the forms.construct_client remains the old method instead of the new one.


@patch_construction("forms")
class FileMoveFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FileMoveForm

    def test_has_fields(self, mock_client_creator):
        """Test that the fields contain the minimally defined fields"""
        self.assertHasField("directory_name")
        self.assertHasField("file_name")

    def test_file_name_field(self, mock_client_creator):
        form = self.build_form(data={})
        name_field = form.fields["file_name"]
        choices = [entry[0] for entry in name_field.choices]
        # See mock_ls for list of contents
        self.assertNotIn("documentation", choices)
        self.assertNotIn("documentation/", choices)
        self.assertIn("new_file.txt", choices)
        self.assertIn("icon_small.png", choices)

    def test_execute_new_folder(self, mock_client: Mock):
        form = self.assertFormValid(data={"file_name": "new_file.txt", "directory_name": "NewFolder"})
        form.execute()
        mock_client().mkdir.assert_called()
        folder = mock_client().mkdir.call_args.args[0]
        self.assertEqual(folder.path, "/NewFolder")
        mock_client().mv.assert_called()
        self.assertEqual(mock_client().mv.call_args.args[0].path, "new_file.txt")
        self.assertEqual(mock_client().mv.call_args.args[1].path, "/NewFolder")

    def test_directory_name_validation(self, mock_client: Mock):
        self.assertFormHasError(
            data={"file_name": "new_file.txt", "directory_name": "/NewFoldeer"}, code="invalid_directory_name"
        )

    def test_execute_existing_folder(self, mock_client: Mock):
        # Set exists return type so it confirms the folder exists
        mock_client.return_value.exists.return_value = True

        form = self.assertFormValid(data={"file_name": "new_file.txt", "directory_name": "documentation/"})
        form.execute()
        mock_client().mkdir.assert_not_called()
        mock_client().mv.assert_called()
        self.assertEqual(mock_client().mv.call_args.args[1].path, "/documentation/")
        self.assertEqual(mock_client().mv.call_args.args[0].path, "new_file.txt")


@patch_construction("forms")
class FileSyncFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = SyncFileToFolderForm

    def setUp(self):
        self.folder = SquireNextCloudFolder.objects.first()
        super(FileSyncFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault("folder", self.folder)
        return super(FileSyncFormTestCase, self).get_form_kwargs(**kwargs)

    def test_has_fields(self, mock_client):
        """Test that the fields contain the minimally defined fields"""
        self.assertHasField("display_name")
        self.assertHasField("description")
        self.assertHasField("selected_file")

    def test_selected_file_field(self, mock_client):
        form = self.build_form(data={})
        name_field = form.fields["selected_file"]
        choices = [entry[0] for entry in name_field.choices]
        # See mock_ls for list of contents
        self.assertNotIn("documentation", choices)
        self.assertNotIn("documentation/", choices)
        self.assertIn("new_file.txt", choices)
        self.assertIn("icon_small.png", choices)

    def test_form_valid(self, mock_client):
        form = self.assertFormValid(
            data={
                "display_name": "New Folder",
                "description": "Test file that does not actually exist",
                "selected_file": "new_file.txt",
            }
        )
        self.assertEqual(form.instance.folder, self.folder)
        self.assertEqual(form.instance.slug, "new-folder")

        self.assertFalse(SquireNextCloudFile.objects.filter(file_name="new_file.txt"))
        form.save()
        self.assertTrue(SquireNextCloudFile.objects.filter(file_name="new_file.txt"))

    def test_form_connection_default(self, mock_client):
        form = self.assertFormValid(
            data={
                "display_name": "New Folder",
                "description": "Test file that does not actually exist",
                "selected_file": "new_file.txt",
            }
        )
        self.assertEqual(form.instance.connection, "NcS")
        self.assertNotIn("connection", form.fields.keys())

    def test_client_calling(self, mock_client):
        form = self.assertFormValid(
            data={
                "display_name": "New Folder",
                "description": "Test file that does not actually exist",
                "selected_file": "new_file.txt",
            }
        )
        form.save()
        mock_client.return_value.mv.assert_called()
        self.assertEqual(mock_client().mv.call_args.args[0].path, "new_file.txt")
        self.assertEqual(mock_client().mv.call_args.args[1].path, "/TestFolder/")


@patch_construction("forms")
class FolderCreateFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FolderCreateForm

    def test_form_valid(self, mock):
        self.assertFormValid(
            data={
                "display_name": "New Folder",
                "description": "Test folder description",
            }
        )

    def test_clean_instance_path(self, mock):
        """Tests that the instance.path is cleaned to a path-format"""
        form = self.assertFormValid(
            data={
                "display_name": "Test name",
                "description": "Test folder description",
            }
        )
        self.assertEqual(form.instance.path, "/test-name/")

    def test_fail_empty_display_names(self, mock):
        self.assertFormHasError(data={"display_name": "    ", "description": "valid description"}, code="required")

    def test_save_creates_folder(self, mock):
        form = self.assertFormValid(
            data={
                "display_name": "testfolder",
                "description": "Test folder description",
            }
        )
        form.save()
        mock.return_value.mkdir.assert_called_with("/testfolder/")
        self.assertTrue(SquireNextCloudFolder.objects.filter(display_name="testfolder").exists())

    def test_do_not_save_instance_on_connection_faillure(self, mock):
        def throw_error(*args, **kwargs):
            raise RuntimeError()

        mock.return_value.mkdir.side_effect = throw_error
        with self.assertRaises(RuntimeError):
            form = self.assertFormValid(
                data={
                    "display_name": "testfolder",
                    "description": "Test folder description",
                }
            )
            form.save()
        self.assertFalse(SquireNextCloudFolder.objects.filter(display_name="testfolder").exists())


class FolderEditFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FolderEditForm

    def get_form_kwargs(self, **kwargs):
        kwargs = super(FolderEditFormTestCase, self).get_form_kwargs(**kwargs)
        kwargs["instance"] = SquireNextCloudFolder.objects.first()
        return kwargs

    def test_fields(self):
        self.assertHasField("display_name")
        self.assertHasField("description")
        self.assertHasField("requires_membership")
        self.assertHasField("on_overview_page")

        # Assert that nextcloud link related fields are not in here
        form = self.build_form(data={})
        self.assertNotIn("path", form.fields)
        self.assertNotIn("is_missing", form.fields)

    def test_form_type(self):
        form = self.build_form(data={})
        self.assertIsInstance(form, ModelForm)


class FileEditFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FileEditForm

    def get_form_kwargs(self, **kwargs):
        kwargs = super(FileEditFormTestCase, self).get_form_kwargs(**kwargs)
        kwargs["instance"] = SquireNextCloudFile.objects.first()
        return kwargs

    def test_fields(self):
        self.assertHasField("display_name")
        self.assertHasField("description")

        # Assert that nextcloud link related fields are not in here
        form = self.build_form(data={})
        self.assertNotIn("file_name", form.fields)
        self.assertNotIn("connection", form.fields)
        self.assertNotIn("is_missing", form.fields)

    def test_form_type(self):
        form = self.build_form(data={})
        self.assertIsInstance(form, ModelForm)


class FileEditFormSetTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FileEditFormset

    def setUp(self):
        super(FileEditFormSetTestCase, self).setUp()
        self.files = SquireNextCloudFile.objects.all()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault("nc_files", self.files)
        kwargs = super(FileEditFormSetTestCase, self).get_form_kwargs(**kwargs)
        return kwargs

    def test_formset_values(self):
        form = self.build_form(data={})
        self.assertEqual(form.min_num, 0)
        self.assertEqual(form.max_num, self.files.count())
        self.assertEqual(form.absolute_max, form.max_num)
        self.assertEqual(form.validate_min, form.max_num)
        self.assertEqual(form.validate_max, form.max_num)
        self.assertEqual(form.can_delete, False)
        self.assertEqual(form.can_order, False)

    def test_validation(self):
        self.assertFormValid(
            data={
                "form-TOTAL_FORMS": 2,
                "form-INITIAL_FORMS": 0,
                "form-MIN_NUM_FORMS": 0,
                "form-MAX_NUM_FORMS": 2,
                "form-0-display_name": "Item 1",
                "form-0-description": "description 1",
                "form-1-display_name": "Item 2",
                "form-1-description": "description 2",
            },
            nc_files=self.files[0:2],
        )

    def test_saving(self):
        form = self.build_form(
            data={
                "form-TOTAL_FORMS": 2,
                "form-INITIAL_FORMS": 0,
                "form-MIN_NUM_FORMS": 0,
                "form-MAX_NUM_FORMS": 2,
                "form-0-display_name": "New item name for 1",
                "form-0-description": "D-1",
                "form-1-display_name": "Item adjusted 2",
                "form-1-description": "D-2",
            },
            nc_files=self.files[0:2],
        )
        form.save()
        self.assertEqual(self.files[0].display_name, "New item name for 1")
        self.assertEqual(self.files[0].description, "D-1")
        self.assertEqual(self.files[1].display_name, "Item adjusted 2")
        self.assertEqual(self.files[1].description, "D-2")


class FolderEditFormGroupTestCase(FormValidityMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    form_class = FolderEditFormGroup

    def test_form_class(self):
        self.assertEqual(self.form_class.form_class, FolderEditForm)
        self.assertEqual(self.form_class.formset_class, FileEditFormset)

    def test_form_build(self):
        self.build_form(data=None, folder=SquireNextCloudFolder.objects.first())
