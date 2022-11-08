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
