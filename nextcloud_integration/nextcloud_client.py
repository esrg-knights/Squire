from django.conf import settings
import xml.etree.cElementTree as xml
from urllib.parse import urlparse
from django.conf import settings
from django.utils.text import slugify

from easywebdav import Client, OperationFailed


from nextcloud_integration.exceptions import ClientNotImplemented
from nextcloud_integration.nextcloud_resources import NextCloudFile, NextCloudFolder, NextCloudResource


__all__ = ["NextCloudFile", "NextCloudFolder"]


"""
Credit goes to EasyWebDav for setting excellent ground work. However due to an error in reading the NextCloud data
and the 8 years of inactivity since the latest update motivated me to branch it for this particular project in the 
source code below.

Original source code:
https://github.com/amnong/easywebdav

"""


class NextCloudClient(Client):
    dav_path = "remote.php/dav/files/"

    def __init__(self, *args, path=None, **kwargs):
        self.local_baseurl = "{local_url}/{username}".format(
            local_url=self.dav_path.strip("/"), username=kwargs.get("username", "")
        )
        if path:
            path = f"{path.strip('/')}/{self.local_baseurl}"
        else:
            path = self.local_baseurl

        super(NextCloudClient, self).__init__(*args, path=path, **kwargs)

    def download(self, file: NextCloudFile):
        """
        Downloads the indicated file from Nextcloud
        :param file: The NextCloudFile to be downloaded
        :return:
        """
        return self._send("GET", file.path, 200, stream=True)

    def mkdir(self, folder):
        if isinstance(folder, NextCloudFolder):
            super(NextCloudClient, self).mkdir(folder.path)
        else:
            super(NextCloudClient, self).mkdir(folder)
            folder = NextCloudFolder(folder)
        return folder

    def ls(self, remote_path=""):
        headers = {"Depth": "1"}
        response = self._send("PROPFIND", remote_path, expected_code=207, headers=headers)

        tree = xml.fromstring(response.content)
        # The bit below is adjusted to take the new constructs into account
        resources = [self.construct_nextcloud_resource(dav_node) for dav_node in tree.findall("{DAV:}response")]
        # It also returns the folder itself, which is redundant, so remove it from the results
        return list(filter(lambda r: r.name != remote_path, resources))

    def mv(self, file: NextCloudFile, to_folder: NextCloudFolder):
        new_path = self._get_url(to_folder.path).strip("/") + "/" + file.path.split("/")[-1]
        headers = {"DESTINATION": new_path}
        self._send("MOVE", file.path, expected_code=201, headers=headers)
        file.path = new_path

    def exists(self, resource: NextCloudResource = None, path: str = None):
        """Determines whether a certain resource or path exists on the nextcloud"""
        assert not (resource and path)
        assert resource or path

        if resource:
            path = resource.path

        res = super(NextCloudClient, self).exists(remote_path=path)

        return res

    def _get_dav_prop(self, elem, name, default=None):
        """Obtain data for the given property or return default if it is not present"""
        child = elem.find(".//{DAV:}" + name)
        return default if child is None or child.text is None else child.text

    def construct_nextcloud_resource(self, dav_node):
        """Factory method for the given method"""
        path = self._get_dav_prop(dav_node, "href")
        path = path[path.index(self.local_baseurl) + len(self.local_baseurl) :]

        # Get the name
        name = path[max(0, path[:-1].rfind("/")) :].replace("%20", " ").strip("/")

        if self._get_dav_prop(dav_node, "getcontentlength") is None:
            return NextCloudFolder(
                path=path,
                name=name,
            )
        else:
            return NextCloudFile(
                path=path,
                name=name,
                last_modified=self._get_dav_prop(dav_node, "getlastmodified", ""),
                content_type=self._get_dav_prop(dav_node, "getcontenttype", ""),
            )


def construct_client():
    try:
        host = settings.NEXTCLOUD_HOST
        username = settings.NEXTCLOUD_USERNAME
        password = settings.NEXTCLOUD_PASSWORD
    except AttributeError:
        raise ClientNotImplemented()
    else:
        return NextCloudClient(
            host=host,
            username=username,
            password=password,
            protocol="https",
            path=getattr(settings, "NEXTCLOUD_URL", ""),  # Local url is optional
        )


# Append OperationFailed operations with additional methods
OperationFailed._OPERATIONS["MOVE"] = "Move file"
