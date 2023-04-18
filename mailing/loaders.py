"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages.
"""

from django.template.utils import get_app_template_dirs
from django.template.loaders.filesystem import Loader as FilesystemLoader


class CustomAppDirectoryLoader(FilesystemLoader):
    folder_name: str

    def __init__(self, engine, folder_name):
        self.folder_name = folder_name
        super(CustomAppDirectoryLoader, self).__init__(engine)

    def get_dirs(self):
        return get_app_template_dirs(self.folder_name)
