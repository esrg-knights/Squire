from unittest.mock import Mock
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile
from unittest.mock import patch

from requests.models import Response


def mock_exists(exists=True):
    """Script that changes the default now time to a preset value"""

    def fake_exists(*args, **kwargs):
        return exists

    return fake_exists


def mock_ls():
    """Script that replaces the is_organiser method returning the initial input of this method (default=True)"""

    def fake_ls(*args, **kwargs):
        entries = [
            NextCloudFolder(path="First%20Folder/"),
            NextCloudFolder(path="TestFolder/"),
            NextCloudFolder(path="documentation/"),
            NextCloudFile(path="new_file.txt"),
            NextCloudFile(path="icon_large.png"),
            NextCloudFile(path="icon_small.png"),
        ]
        return entries

    return fake_ls


def mock_mkdir():
    """Mock mkdir method. It should return the folder it is given"""

    def fake_mkdir(nextcloud_folder, *args, **kwargs):
        return nextcloud_folder

    return fake_mkdir


def patch_construction(source_name, exists=False):
    """Extends the patch decorator to intercept client related functionality with base testing functions
    :param source_name Name of the source that needs interjecting. Ie forms, models or whatever. Because the local reference
    occurs before this method triggers, calling the nextcloud_client source is not sufficient.
    :param exists Whether the exists function should return True
    """
    patch_output = patch(
        **{
            "target": f"nextcloud_integration.{source_name}.construct_client",
            "return_value.ls.return_value": mock_ls()(),
            "return_value.exists.return_value": mock_exists(exists)(),
            "return_value.mkdir.side_effect": mock_mkdir(),
        }
    )
    return patch_output
