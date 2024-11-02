from django.test import TestCase
from os.path import exists as file_exists
from requests.models import Response

from unittest.mock import patch

from nextcloud_integration.nextcloud_client import NextCloudClient as Client
from nextcloud_integration.nextcloud_client import construct_client
from nextcloud_integration.nextcloud_resources import (
    NextCloudFolder,
    NextCloudFile,
    get_file_type,
    WordFileType,
    AbstractFileType,
    CompressedFileType,
    CreativeFileType,
    ExcelFileType,
    ImageFileType,
    PDFFileType,
    PowerpointFileType,
    TextFileType,
)


class NextCloudClientTestCase(TestCase):
    def setUp(self):
        self.client = Client(
            host="example.com",
            username="example_user",
            password="example_pw",
            protocol="https",
            path="",
        )

    def _construct_send_response(self, file_name=None, status_code=None):
        """
        Constructs an imitation of a request response
        :param file_name: The name of the file in tests/files to load as content
        :param status_code: The HTTP status code
        :return:
        """
        resp = Response()
        file_name = file_name or "non_existent.dat"
        file_path = f"nextcloud_integration/tests/files/{file_name}"
        if file_name is not None and file_exists(file_path):
            with open(file_path, "r") as file:
                resp._content = file.read()
        resp.status_code = status_code or 200
        return resp

    def _patch_send(self, side_effect=None, file_name=None, status_code=None):
        assert side_effect or file_name or status_code
        assert not (side_effect and file_name)
        assert not (side_effect and status_code)

        if side_effect is None:
            side_effect = [self._construct_send_response(file_name=file_name, status_code=status_code)]

        return patch("nextcloud_integration.nextcloud_client.NextCloudClient._send", side_effect=side_effect)

    def test_ls(self):
        with self._patch_send(file_name="ls_response.xml", status_code=207) as mock:
            response = self.client.ls()

            # Test send data
            self.assertEqual(mock.call_args.args[0], "PROPFIND")
            self.assertEqual(mock.call_args.kwargs["expected_code"], 207)
            self.assertEqual(mock.call_args.kwargs["headers"]["Depth"], "1")

            # Test responses
            nc_folders = {}
            nc_files = {}
            for item in response:
                if isinstance(item, NextCloudFolder):
                    nc_folders[item.name] = item
                elif isinstance(item, NextCloudFile):
                    nc_files[item.name] = item

            self.assertIn("Some Folder", nc_folders.keys())
            self.assertIn("Testnewfolder", nc_folders.keys())
            self.assertIn("test_file.md", nc_files.keys())
            self.assertIn("proof_of_shadowboard.png", nc_files.keys())

    def test_exists(self):
        self.assertRaises(AssertionError, self.client.exists)
        with self._patch_send(status_code=207):
            self.assertEqual(self.client.exists(path="some_existing_file.txt"), True)
        with self._patch_send(status_code=404):
            self.assertEqual(self.client.exists(path="non_existing_file.txt"), False)

        resource = NextCloudFolder(
            path="exampleFolder/",
            name="exampleFolder",
        )
        # Not both a resource and a path should be given
        self.assertRaises(AssertionError, self.client.exists, resource=resource, path="fake/")

        with self._patch_send(status_code=200):
            self.assertEqual(self.client.exists(resource=resource), True)
        with self._patch_send(status_code=404):
            self.assertEqual(self.client.exists(resource=resource), False)

    def test_mv(self):
        folder = NextCloudFolder(
            path="exampleFolder/",
            name="exampleFolder",
        )
        file = NextCloudFile(
            path="oldLocation/example.file",
            name="example.file",
        )

        with self._patch_send(status_code=201) as mock:
            self.client.mv(file, folder)

            new_path = "https://example.com:443/remote.php/dav/files/example_user/exampleFolder/example.file"
            # Test send data
            self.assertEqual(mock.call_args.args[0], "MOVE")
            self.assertEqual(mock.call_args.kwargs["expected_code"], 201)
            self.assertEqual(mock.call_args.kwargs["headers"]["DESTINATION"], new_path)

            self.assertEqual(file.path, new_path)

    def test_mkdir_from_path(self):
        with self._patch_send(status_code=201) as mock:
            self.client.mkdir("Testnewfolder/New%20Folder")

            self.assertEqual(mock.call_args.args[0], "MKCOL")
            self.assertEqual(mock.call_args.args[1], "Testnewfolder/New%20Folder")
            self.assertEqual(mock.call_args.args[2], 201)

    def test_mkdir_from_folder(self):
        with self._patch_send(status_code=201) as mock:
            folder = NextCloudFolder("TestNewFolder/FolderInstance")
            self.client.mkdir(folder)

            self.assertEqual(mock.call_args.args[0], "MKCOL")
            self.assertEqual(mock.call_args.args[1], "TestNewFolder/FolderInstance")
            self.assertEqual(mock.call_args.args[2], 201)

    def test_download_stream(self):
        with self._patch_send(status_code=201) as mock:
            file = NextCloudFolder("files/testfile.txt")
            self.client.download(file)

            self.assertEqual(mock.call_args.args[0], "GET")
            self.assertEqual(mock.call_args.args[1], "files/testfile.txt")
            self.assertEqual(mock.call_args.args[2], 200)
            self.assertEqual(mock.call_args.kwargs.get("stream", None), True)

    @patch("nextcloud_integration.nextcloud_client.NextCloudClient")
    def test_constructor(self, mock_client):
        with self.settings(
            NEXTCLOUD_HOST="test.nl",
            NEXTCLOUD_USERNAME="user_account",
            NEXTCLOUD_PASSWORD="user_password",
            NEXTCLOUD_URL=None,
        ):
            construct_client()
            self.assertEqual(mock_client.call_args.kwargs["host"], "test.nl")
            self.assertEqual(mock_client.call_args.kwargs["username"], "user_account")
            self.assertEqual(mock_client.call_args.kwargs["password"], "user_password")
            self.assertEqual(mock_client.call_args.kwargs["protocol"], "https")
            self.assertEqual(mock_client.call_args.kwargs["path"], None)

        with self.settings(
            NEXTCLOUD_HOST="test.nl",
            NEXTCLOUD_USERNAME="user_account",
            NEXTCLOUD_PASSWORD="user_password",
            NEXTCLOUD_URL="local_url/",
        ):
            construct_client()
            self.assertEqual(mock_client.call_args.kwargs["path"], "local_url/")

    def test_baseurl(self):
        """Test functioning of the client base_url being adjusted if a special path is given"""
        client = Client(
            host="example.com",
            username="example_user",
            password="example_pw",
            protocol="https",
        )
        self.assertEqual(client.baseurl, "https://example.com:443/remote.php/dav/files/example_user")
        # Path inserts a local url on the server indicating the location of the Nextcloud
        # From here the client appends the local url of the nextcloud API
        # Thus ensure that if a path is given, the path is appended in between the host and the nextcloud api url
        client = Client(
            host="example.com",
            username="example_user",
            password="example_pw",
            protocol="https",
            path="/unique_url/",
        )
        self.assertEqual(client.baseurl, "https://example.com:443/unique_url/remote.php/dav/files/example_user")
        client = Client(
            host="example.com",
            username="example_user",
            password="example_pw",
            protocol="https",
            path="unique_url/cloud",
        )
        # Test that first and last dashes are irrelvant
        self.assertEqual(client.baseurl, "https://example.com:443/unique_url/cloud/remote.php/dav/files/example_user")


class FileTypeTestCase(TestCase):
    """Tests file type returns"""

    def assertExpectedFileType(self, file_name, file_type_class):
        file_type = get_file_type(file_name)
        if file_type != file_type_class:
            raise AssertionError(f"{file_name} did not yield {file_type_class}, but {file_type} instead")

    def test_word_file_type(self):
        self.assertExpectedFileType("name.doc", WordFileType)
        self.assertExpectedFileType("name.docx", WordFileType)
        self.assertExpectedFileType("name.odt", WordFileType)

    def test_text_file_type(self):
        self.assertExpectedFileType("name.txt", TextFileType)
        self.assertExpectedFileType("name.md", TextFileType)

    def test_pdf_file_type(self):
        self.assertExpectedFileType("name.pdf", PDFFileType)

    def test_powerpoint_file_type(self):
        self.assertExpectedFileType("name.ppt", PowerpointFileType)
        self.assertExpectedFileType("name.pptx", PowerpointFileType)
        self.assertExpectedFileType("name.odp", PowerpointFileType)

    def test_compressed_file_type(self):
        self.assertExpectedFileType("name.zip", CompressedFileType)
        self.assertExpectedFileType("name.7zip", CompressedFileType)
        self.assertExpectedFileType("name.rar", CompressedFileType)

    def test_excel_file_type(self):
        self.assertExpectedFileType("name.xls", ExcelFileType)
        self.assertExpectedFileType("name.xlsx", ExcelFileType)
        self.assertExpectedFileType("name.odx", ExcelFileType)
        self.assertExpectedFileType("name.csv", ExcelFileType)

    def test_creative_file_type(self):
        self.assertExpectedFileType("name.indd", CreativeFileType)
        self.assertExpectedFileType("name.psd", CreativeFileType)
        self.assertExpectedFileType("name.psb", CreativeFileType)
        self.assertExpectedFileType("name.ai", CreativeFileType)
        self.assertExpectedFileType("name.svg", CreativeFileType)
        self.assertExpectedFileType("name.eps", CreativeFileType)

    def test_default_file_type(self):
        self.assertExpectedFileType("name.xxx", AbstractFileType)
        self.assertExpectedFileType("name", AbstractFileType)
