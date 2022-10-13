from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile, get_file_type
from nextcloud_integration.nextcloud_client import construct_client


class NCFolder(models.Model):
    """ Represents a folder on the nextcloud storage """
    display_name = models.CharField(help_text="Name displayed in Squire", max_length=32)
    slug = models.SlugField()
    description = models.CharField(max_length=256)
    path = models.CharField(help_text="The path to the folder (including the folder itself)",
                            max_length=64, blank=True, default=None)
    folder: NextCloudFolder = None  # Used to translate Nextcloud folder contents

    # Define status for the link to Nextcloud
    is_missing = models.BooleanField(default=False) # Whether the folder is non-existant on nextcloud

    def __init__(self, *args, **kwargs):
        super(NCFolder, self).__init__(*args, **kwargs)
        if self.id:
            self.folder = NextCloudFolder(path=self.path)

    def clean(self):
        if self.folder is None and self.path is None:
            raise ValidationError("Either path or folder should be defined")

    def save(self, **kwargs):
        if self.folder and self.path == "":
            self.path = self.folder.path

        if self.slug is None or self.slug == "":
            self.slug = slugify(self.display_name)

        return super(NCFolder, self).save(**kwargs)

    def exists_on_nextcloud(self):
        """ Checks whether the folder exists on the nextcloud """
        client = construct_client()
        return client.exists(self.folder)

    def __str__(self):
        return f"Folder: {self.display_name}"

    def get_absolute_url(self):
        return reverse("nextcloud:folder_view", kwargs={'folder_slug': self.slug})


class NCFile(models.Model):
    """ Represents a file on the nextcloud storage """
    display_name = models.CharField(help_text="Name displayed in Squire", max_length=32)
    description = models.CharField(max_length=256, blank=True)
    file_name = models.CharField(help_text="The file name", max_length=64, blank=True, default=None)
    folder = models.ForeignKey(NCFolder, on_delete=models.CASCADE, related_name="files")
    slug = models.SlugField(blank=True)
    file: NextCloudFolder = None  # Used to translate Nextcloud folder contents

    is_missing = models.BooleanField(default=False) # Whether the file is non-existant on nextcloud
    connection = models.CharField(max_length=3, choices=[
        ("NcS", "Synched through file on Nextcloud"),
        ("SqU", "Uploaded through Squire")
    ]) # Defines how the connection occured

    def __init__(self, *args, **kwargs):
        super(NCFile, self).__init__(*args, **kwargs)
        if self.id:
            self.file = NextCloudFile(path=self.path)

    def save(self, **kwargs):
        if self.file and self.file_name == "":
            self.file_name = self.file.name

        if self.slug is None or self.slug == "":
            self.slug = slugify(self.file_name.replace('.', '_'))

        return super(NCFile, self).save(**kwargs)

    def clean(self):
        if self.file is None and (self.file_name is None or self.file_name == ""):
            raise ValidationError("Either file or filename should be defined")

    def exists_on_nextcloud(self):
        """ Checks whether the folder exists on the nextcloud """
        client = construct_client()
        return client.exists(self.file)

    def __str__(self):
        return f"File: {self.display_name}"

    @property
    def path(self):
        return f"{self.folder.path}{self.file_name}"

    def get_absolute_url(self):
        return reverse("nextcloud:file_dl", kwargs={
            'folder_slug': self.folder.slug,
            'file_slug': self.slug,
        })

    def get_file_type(self):
        return get_file_type(self.file_name)
