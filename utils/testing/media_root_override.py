import os

from django.test import override_settings
from django.conf import settings


def set_media_test_folder():
    """ Use as a decorator to set media root to test/files. Ideal for filefield instances defined in fixtures """
    media_folder = os.path.join(settings.BASE_DIR, 'test', 'files')

    class UseTestMediaRootMixin(override_settings):

        def __init__(self, **kwargs):
            kwargs.update({
                'MEDIA_ROOT': media_folder,
            })
            super(UseTestMediaRootMixin, self).__init__(**kwargs)

    return UseTestMediaRootMixin


# The decorator to overwrite the media folder to the test reports
override_media_folder = set_media_test_folder()
