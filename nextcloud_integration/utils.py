from nextcloud_integration.models import SquireNextCloudFolder
from nextcloud_integration.nextcloud_client import construct_client


def refresh_status(folder: SquireNextCloudFolder):
    """Refreshes the status of the folder and it's contents
    :param folder: The nextcloud folder validated
    :return True if all files were present on Squire
    """
    client = construct_client()

    if not client.exists(resource=folder.folder):
        folder.is_missing = True
        folder.save()
        return False

    folder.files.update(is_missing=False)

    all_ok = True
    for file in folder.files.all():
        if not client.exists(resource=file.file):
            file.is_missing = True
            file.save()
            all_ok = False

    return all_ok
