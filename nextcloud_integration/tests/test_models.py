from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from nextcloud_integration.models import NCFile, NCFolder
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile


class NCFileTestcase(TestCase):
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


class NCFolderTestcase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def test_slugify(self):
        folder = NCFolder.objects.create(
            display_name="Test slug",
            path="/A fake path/",
        )
        self.assertEqual(folder.slug, "test-slug")
