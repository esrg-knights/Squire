from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile


def mock_exists(exists=True):
    """ Script that changes the default now time to a preset value """
    def fake_exists(*args, **kwargs):
        return exists

    return fake_exists


def mock_ls():
    """ Script that replaces the is_organiser method returning the initial input of this method (default=True) """
    def fake_ls(*args, **kwargs):
        entries = [
            NextCloudFolder(path="First%20Folder/"),
            NextCloudFolder(path="documentation/"),
            NextCloudFile(path="new_file.txt"),
            NextCloudFile(path="icon_large.png"),
            NextCloudFile(path="icon_small.png"),
        ]
        return entries

    return fake_ls


class MockClient:
    """ Fake Nextcloud client used for testing purposes """

    def __init__(self, files_exist=False, **kwargs):
        self.kwargs = kwargs
        self.ls = mock_ls()
        self.exists = mock_exists(files_exist)


def construct_fake_client(files_exist=False):
    def construct_client():
        return MockClient(files_exist=files_exist)
    return construct_client
