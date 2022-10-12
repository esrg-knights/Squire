from django.test import TestCase

from nextcloud_integration.nextcloud_client import NextCloudClient as Client

web_data = {
    'website': 'beta.kotkt.nl',
    'local_a': 'nextcloud/remote.php/dav/files/squire',
    'username': 'squire',
    'password':  'vENRJ87ksiXU5Rj',
}


class WebDavTests(TestCase):

    def test_this(self):
        webdav = Client(
            host=web_data['website'],
            username=web_data['username'],
            password=web_data['password'],
            protocol='https',
            path=web_data['local_a'],
        )

        # webdav._send = types.MethodType(new_send, webdav)

        # webdav.ls()
        print([str(a) for a in webdav.ls(remote_path='')])




