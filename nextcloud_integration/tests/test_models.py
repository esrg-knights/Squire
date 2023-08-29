from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from nextcloud_integration.models import SquireNextCloudFile, SquireNextCloudFolder
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile

from . import patch_construction


class NCFileTestCase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def test_slugify(self):
        file = SquireNextCloudFile.objects.create(
            display_name="Test slug", file_name="Arbitrary file name.test", folder_id=1
        )
        self.assertEqual(file.slug, "test-slug")

    def test_slug_unique_together(self):
        with self.assertRaises(ValidationError) as e:
            file = SquireNextCloudFile(
                display_name="Display name",
                file_name="Arbitrary file name.test",
                folder_id=1,
                slug="initial_file",
            )
            file.full_clean()
        self.assertEqual(e.exception.error_dict["__all__"][0].code, "unique_together")

    def test_file_name_unique_together(self):
        with self.assertRaises(ValidationError) as e:
            file = SquireNextCloudFile(
                display_name="Display name",
                file_name="testfile.md",
                folder_id=1,
                slug="some_slug",
            )
            file.full_clean()
        self.assertEqual(e.exception.error_dict["__all__"][0].code, "unique_together")

    def test_get_absolute_url(self):
        file = SquireNextCloudFile.objects.get(id=1)
        self.assertEqual(
            file.get_absolute_url(),
            reverse(
                "nextcloud:file_dl",
                kwargs={
                    "folder_slug": file.folder.slug,
                    "file_slug": file.slug,
                },
            ),
        )

    def test_path_or_file_validation_on_new_instance(self):
        with self.assertRaises(ValidationError) as e:
            file = SquireNextCloudFile(
                display_name="Test slug",
                folder_id=1,
                connection="SqU",
            )
            file.full_clean()
        self.assertEqual(e.exception.error_dict["__all__"][0].code, "no_file_name_linked")

        # Supplying a nextcloud file should suppress the issue
        file = SquireNextCloudFile(
            display_name="Test slug",
            folder_id=1,
            connection="SqU",
        )
        file.file = NextCloudFile(path="/fake_file.txt")
        file.full_clean()

        # Supplying a filename should suppress the issue
        file = SquireNextCloudFile(display_name="Test slug", folder_id=1, connection="SqU", file_name="fake_file.txt")
        file.full_clean()

    def test_path(self):
        file = SquireNextCloudFile.objects.get(id=1)
        self.assertEqual(file.path, "/TestFolder/testfile.md")

    def test_file_name_from_nextcloud_file_instance(self):
        file = SquireNextCloudFile(folder=SquireNextCloudFolder.objects.first())
        file.file = NextCloudFile("testfile.txt")
        file.save()
        self.assertEqual(file.file_name, "testfile.txt")

    @patch_construction("models")
    def test_exists_on_nextcloud(self, mock_client):
        mock_client.return_value.exists.return_value = False
        self.assertEqual(SquireNextCloudFile.objects.first().exists_on_nextcloud(), False)
        mock_client.return_value.exists.return_value = True
        self.assertEqual(SquireNextCloudFile.objects.first().exists_on_nextcloud(), True)

    def test_str(self):
        self.assertEqual(str(SquireNextCloudFile.objects.first()), "File: Initial file")


class NCFolderTestcase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def test_slugify(self):
        folder = SquireNextCloudFolder.objects.create(
            display_name="Test slug",
            path="/A fake path/",
        )
        self.assertEqual(folder.slug, "test-slug")

    def test_path_or_file_validation_on_new_instance(self):
        with self.assertRaises(ValidationError):
            folder = SquireNextCloudFolder(
                display_name="Test folder",
                description="",
            )
            folder.full_clean()

        # Supplying a nextcloud file should suppress the issue
        folder = SquireNextCloudFolder(
            display_name="Test folder",
            description="",
        )
        folder.folder = NextCloudFolder(path="/Test Folder")
        folder.full_clean()

        # Supplying a filename should suppress the issue
        folder = SquireNextCloudFolder(display_name="Test folder", description="", path="Test folder")
        folder.full_clean()

    def test_file_name_from_nextcloud_file_instance(self):
        folder = SquireNextCloudFolder()
        folder.folder = NextCloudFolder("Test Folder")
        folder.save()
        self.assertEqual(folder.path, "Test Folder")

    @patch_construction("models")
    def test_exists_on_nextcloud(self, mock_client):
        mock_client.return_value.exists.return_value = False
        self.assertEqual(SquireNextCloudFolder.objects.first().exists_on_nextcloud(), False)
        mock_client.return_value.exists.return_value = True
        self.assertEqual(SquireNextCloudFolder.objects.first().exists_on_nextcloud(), True)

    def test_str(self):
        self.assertEqual(str(SquireNextCloudFolder.objects.first()), "Folder: Initial folder")
