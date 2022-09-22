import requests
from numbers import Number
from django.conf import settings
import xml.etree.cElementTree as xml
from http.client import responses as HTTP_CODES
from urllib.parse import urlparse
from django.utils.text import slugify

from easywebdav import Client, OperationFailed



from nextcloud_integration.nextcloud_resources import NextCloudFile, NextCloudFolder, NextCloudResource


__all__ = ['NextCloudFile', 'NextCloudFolder']


"""
Credit goes to EasyWebDav for setting excellent ground work. However due to an error in reading the NextCloud data
and the 8 years of inactivity since the latest update motivated me to branch it for this particular project in the 
source code below.

Original source code:
https://github.com/amnong/easywebdav

"""


nextcloud_path = "/nextcloud/remote.php/dav/files/squire/"


def get_dav_prop(elem, name, default=None):
    """ Obtain data for the given property or return default if it is not present """
    child = elem.find('.//{DAV:}' + name)
    return default if child is None or child.text is None else child.text


def construct_nextcloud_resource(dav_node):
    """ Factory method for the given method """
    path=get_dav_prop(dav_node, 'href')[len(nextcloud_path):]

    # Get the name
    name = path[max(0, path[:-1].rfind('/')):].replace('%20', ' ').strip('/')

    if get_dav_prop(dav_node, 'getcontentlength') is None:
        return NextCloudFolder(
            path=path,
            name=name,
        )
    else:
        return NextCloudFile(
            path=path,
            name=name,
            last_modified=get_dav_prop(dav_node, 'getlastmodified', ''),
            content_type=get_dav_prop(dav_node, 'getcontenttype', ''),
        )


class NextCloudClient(Client):
    def download(self, file: NextCloudFile):
        local_file_path = '{0}\\{1}\\{2}'.format(
            settings.MEDIA_ROOT,
            'NextCloud',
            file.name,
        )

        super.download(file.path, local_file_path)

        return local_file_path

    def mkdir(self, folder):
        if isinstance(folder, NextCloudFolder):
            super(NextCloudClient, self).mkdir(folder.path)
        else:
            super(NextCloudClient, self).mkdir(folder)
            folder = NextCloudFolder(folder)
        return folder



    def ls(self, remote_path=''):
        headers = {'Depth': '1'}
        response = self._send('PROPFIND', remote_path, (207, 301), headers=headers)

        # Redirect
        if response.status_code == 301:
            url = urlparse(response.headers['location'])
            return self.ls(url.path)

        tree = xml.fromstring(response.content)
        # The bit below is adjusted to take the new constructs into account
        resources = [construct_nextcloud_resource(dav_node) for dav_node in tree.findall('{DAV:}response')]
        # It also returns the folder itself, which is redundant, so remove it from the results
        return list(filter(lambda r: r.name != remote_path, resources))

    def mv(self, file:NextCloudFile, to_folder: NextCloudFolder):
        headers = {'DESTINATION': self._get_url(to_folder.path).strip('/')+'/'+file.path.split('/')[-1]}
        self._send('MOVE', file.path, 201, headers=headers)

    def exists(self, resource:NextCloudResource=None, path:str=None):
        """ Determines whether a certain resource or path exists on the nextcloud """
        assert not (resource and path)
        assert resource or path

        if resource:
            path = resource.path

        print(path)

        return super(NextCloudClient, self).exists(remote_path=path)



def construct_client():
    web_data = {
        'website': 'beta.kotkt.nl',
        'local_a': 'nextcloud/remote.php/dav/files/squire',
        'username': 'squire',
        'password':  'vENRJ87ksiXU5Rj',
    }
    return NextCloudClient(
        host=web_data['website'],
        username=web_data['username'],
        password=web_data['password'],
        protocol='https',
        path=web_data['local_a'],
    )




# Append OperationFailed operations with additional methods
OperationFailed._OPERATIONS['MOVE'] = "Move file"
