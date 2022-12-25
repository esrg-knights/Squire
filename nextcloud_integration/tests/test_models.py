from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from nextcloud_integration.models import NCFile, NCFolder
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile

from . import patch_construction


class NCFileTestCase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def test_slugify(self):
        file = NCFile.objects.create(
            display_name="Test slug",
            file_name="Arbitrary file name.test",
            folder_id=1
        )
        self.assertEqual(file.slug, "arbitrary-file-name_test")

    def test_get_absolute_url(self):
        file = NCFile.objects.get(id=1)
        self.assertEqual(
            file.get_absolute_url(),
            reverse("nextcloud:file_dl", kwargs={
                'folder_slug': file.folder.slug,
                'file_slug': file.slug,
            })
        )

    def test_path_or_file_validation_on_new_instance(self):
        with self.assertRaises(ValidationError):
            file = NCFile(
                display_name="Test slug",
                folder_id=1,
                connection="SqU",
            )
            file.full_clean()

        # Supplying a nextcloud file should suppress the issue
        file = NCFile(
            display_name="Test slug",
            folder_id=1,
            connection="SqU",
        )
        file.file = NextCloudFile(path="/fake_file.txt")
        file.full_clean()

        # Supplying a filename should suppress the issue
        file = NCFile(
            display_name="Test slug",
            folder_id=1,
            connection="SqU",
            file_name="fake_file.txt"
        )
        file.full_clean()

    def test_path(self):
        file = NCFile.objects.get(id=1)
        self.assertEqual(file.path, "/TestFolder/testfile.md")

    def test_file_name_from_nextcloud_file_instance(self):
        file = NCFile(folder=NCFolder.objects.first())
        file.file = NextCloudFile("testfile.txt")
        file.save()
        self.assertEqual(file.file_name, "testfile.txt")

    @patch_construction('models')
    def test_exists_on_nextcloud(self, mock_client):
        mock_client.return_value.exists.return_value = False
        self.assertEqual(NCFile.objects.first().exists_on_nextcloud(), False)
        mock_client.return_value.exists.return_value = True
        self.assertEqual(NCFile.objects.first().exists_on_nextcloud(), True)

    def test_str(self):
        self.assertEqual(str(NCFile.objects.first()), "File: Initial file")


class NCFolderTestcase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def test_slugify(self):
        folder = NCFolder.objects.create(
            display_name="Test slug",
            path="/A fake path/",
        )
        self.assertEqual(folder.slug, "test-slug")

    def test_path_or_file_validation_on_new_instance(self):
        with self.assertRaises(ValidationError):
            folder = NCFolder(
                display_name="Test folder",
                description="",
            )
            folder.full_clean()

        # Supplying a nextcloud file should suppress the issue
        folder = NCFolder(
            display_name="Test folder",
            description="",
        )
        folder.folder = NextCloudFolder(path="/Test Folder")
        folder.full_clean()

        # Supplying a filename should suppress the issue
        folder = NCFolder(
            display_name="Test folder",
            description="",
            path="Test folder"
        )
        folder.full_clean()

    def test_file_name_from_nextcloud_file_instance(self):
        folder = NCFolder()
        folder.folder = NextCloudFolder("Test Folder")
        folder.save()
        self.assertEqual(folder.path, "Test Folder")

    @patch_construction('models')
    def test_exists_on_nextcloud(self, mock_client):
        mock_client.return_value.exists.return_value = False
        self.assertEqual(NCFolder.objects.first().exists_on_nextcloud(), False)
        mock_client.return_value.exists.return_value = True
        self.assertEqual(NCFolder.objects.first().exists_on_nextcloud(), True)

    def test_str(self):
        self.assertEqual(str(NCFolder.objects.first()), "Folder: Initial folder")
