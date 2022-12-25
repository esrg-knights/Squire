from django.test import TestCase
from os.path import exists as file_exists
from requests.models import Response

from unittest.mock import patch

from nextcloud_integration.nextcloud_client import NextCloudClient as Client
from nextcloud_integration.nextcloud_client import construct_client
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile


class NextCloudClientTestCase(TestCase):

    def setUp(self):
        self.client = Client(
            host="example.com",
            username="example_user",
            password="example_pw",
            protocol='https',
            path="",
        )

        def last_send(*args, **kwargs):
            """ Replaces the send arguments by storing the arguments and returning a fake response if present """
            self.client._send_data = {
                'args': args,
                'kwargs': kwargs,
            }
            if getattr(self.client, "send_response", None) is not None:
                return self.client.send_response
            else:
                class FailOnCall:
                    def __getattr__(self, item):
                        raise RuntimeError("A response is being tested, but no response was defined. "
                                           "Run 'set_end_response' on the testcase prior to running the test.")
                return FailOnCall()

        self.client._send = last_send

    def set_send_response(self, file_name=None, status_code=None):
        """
        Sets an imitation for a response
        :param file_name: The name of the file in tests/files to load as content
        :param status_code: The HTTP status code
        :return:
        """
        resp = Response()
        file_path = f"nextcloud_integration/tests/files/{file_name}"
        if file_name is not None and file_exists(file_path):
            with open(file_path, "r") as file:
                resp._content = file.read()
        resp.status_code = status_code or 200

        self.client.send_response = resp

    def test_ls(self):
        self.set_send_response("ls_response.xml", status_code=207)
        response = self.client.ls()

        # Test send data
        self.assertEqual(self.client._send_data["args"][0], "PROPFIND")
        self.assertEqual(self.client._send_data["kwargs"]["expected_code"], (207, 301))
        self.assertEqual(self.client._send_data["kwargs"]["headers"]["Depth"], '1')

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

    def test_ls_redirect(self):
        # Todo: adjust testing logic so that url is intercepted for testing
        pass

    def test_exists(self):
        self.assertRaises(AssertionError, self.client.exists)
        self.set_send_response("exam.ple", status_code=200)
        self.assertEqual(self.client.exists(path="some_existing_file.txt"), True)
        self.set_send_response("exam.ple", status_code=404)
        self.assertEqual(self.client.exists(path="non_existing_file.txt"), False)

        resource = NextCloudFolder(
            path="exampleFolder/",
            name="exampleFolder",
        )
        # Not both a resource and a path should be given
        self.assertRaises(AssertionError, self.client.exists, resource=resource, path="fake/")
        self.set_send_response("exam.ple", status_code=200)
        self.assertEqual(self.client.exists(resource=resource), True)
        self.set_send_response("exam.ple", status_code=404)
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
        self.set_send_response(status_code=201)
        self.client.mv(file, folder)

        new_path = "https://example.com:443/remote.php/dav/files/example_user/exampleFolder/example.file"
        # Test send data
        self.assertEqual(self.client._send_data["args"][0], "MOVE")
        self.assertEqual(self.client._send_data["kwargs"]["expected_code"], 201)
        self.assertEqual(self.client._send_data["kwargs"]["headers"]["DESTINATION"], new_path)

        self.assertEqual(file.path, new_path)

    def test_mkdir_from_path(self):
        self.set_send_response(status_code=201)
        self.client.mkdir("Testnewfolder/New%20Folder")

        self.assertEqual(self.client._send_data["args"][0], "MKCOL")
        self.assertEqual(self.client._send_data["args"][1], "Testnewfolder/New%20Folder")
        self.assertEqual(self.client._send_data["args"][2], 201)

    def test_mkdir_from_folder(self):
        self.set_send_response(status_code=201)
        folder = NextCloudFolder("TestNewFolder/FolderInstance")
        self.client.mkdir(folder)

        self.assertEqual(self.client._send_data["args"][0], "MKCOL")
        self.assertEqual(self.client._send_data["args"][1], "TestNewFolder/FolderInstance")
        self.assertEqual(self.client._send_data["args"][2], 201)

    def test_download_stream(self):
        self.set_send_response(status_code=201)
        file = NextCloudFolder("files/testfile.txt")
        self.client.download(file)

        self.assertEqual(self.client._send_data["args"][0], "GET")
        self.assertEqual(self.client._send_data["args"][1], "files/testfile.txt")
        self.assertEqual(self.client._send_data["args"][2], 200)
        self.assertEqual(self.client._send_data["kwargs"].get('stream', None), True)

    @patch('nextcloud_integration.nextcloud_client.NextCloudClient')
    def test_constructor(self, mock_client):
        with self.settings(
            NEXTCLOUD_HOST="test.nl",
            NEXTCLOUD_USERNAME="user_account",
            NEXTCLOUD_PASSWORD="user_password",
        ):
            construct_client()
            self.assertEqual(mock_client.call_args.kwargs['host'], "test.nl")
            self.assertEqual(mock_client.call_args.kwargs['username'], "user_account")
            self.assertEqual(mock_client.call_args.kwargs['password'], "user_password")
            self.assertEqual(mock_client.call_args.kwargs['protocol'], "https")
            self.assertEqual(mock_client.call_args.kwargs['path'], "")

        with self.settings(
            NEXTCLOUD_HOST="test.nl",
            NEXTCLOUD_USERNAME="user_account",
            NEXTCLOUD_PASSWORD="user_password",
            NEXTCLOUD_URL="local_url/"
        ):
            construct_client()
            self.assertEqual(mock_client.call_args.kwargs['path'], "local_url/")
