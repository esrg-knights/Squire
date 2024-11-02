from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile, get_file_type
from nextcloud_integration.nextcloud_client import construct_client


class SquireNextCloudFolder(models.Model):
    """Represents a folder on the nextcloud storage"""

    display_name = models.CharField(help_text="Name displayed in Squire", max_length=64)
    slug = models.SlugField(blank=True, unique=True)
    description = models.CharField(max_length=256, blank=True)
    path = models.CharField(
        help_text="The path to the folder (including the folder itself)", max_length=64, blank=True, default=None
    )
    folder: NextCloudFolder = None  # Used to translate Nextcloud folder contents

    # Define status for the link to Nextcloud
    is_missing = models.BooleanField(default=False)  # Whether the folder is non-existant on nextcloud

    # Access settings
    requires_membership = models.BooleanField(default=True)
    on_overview_page = models.BooleanField(
        default=True, help_text="Whether this folder is displayed on the " "association download page"
    )

    def __init__(self, *args, **kwargs):
        super(SquireNextCloudFolder, self).__init__(*args, **kwargs)
        if self.id:
            self.folder = NextCloudFolder(path=self.path)

    def clean(self):
        if self.folder is None and self.path is None:
            raise ValidationError("Either path or folder should be defined")

    def save(self, **kwargs):
        if self.folder and (self.path is None or self.path == ""):
            self.path = self.folder.path
            update_fields: set = kwargs.get("update_fields")
            if update_fields is not None and "folder" in update_fields:
                kwargs["update_fields"].add("path")

        if self.slug is None or self.slug == "":
            self.slug = slugify(self.display_name)

        return super(SquireNextCloudFolder, self).save(**kwargs)

    def exists_on_nextcloud(self):
        """Checks whether the folder exists on the nextcloud"""
        client = construct_client()
        return client.exists(self.folder)

    def __str__(self):
        return f"Folder: {self.display_name}"


class SquireNextCloudFile(models.Model):
    """Represents a file on the nextcloud storage"""

    display_name = models.CharField(help_text="Name displayed in Squire", max_length=64)
    description = models.CharField(max_length=256, blank=True)
    file_name = models.CharField(help_text="The file name", max_length=64, blank=True, default=None)
    folder = models.ForeignKey(SquireNextCloudFolder, on_delete=models.CASCADE, related_name="files")
    slug = models.SlugField(blank=True)
    file: NextCloudFolder = None  # Used to translate Nextcloud folder contents

    is_missing = models.BooleanField(default=False)  # Whether the file is non-existant on nextcloud
    CONNECTION_NEXTCLOUD_SYNC = "NcS"
    CONNECTION_SQUIRE_UPLOAD = "SqU"
    CONNECTION_MANUAL = "Mnl"
    connection = models.CharField(
        max_length=3,
        default=CONNECTION_MANUAL,
        choices=[
            (CONNECTION_NEXTCLOUD_SYNC, "Synched through file on Nextcloud"),
            (CONNECTION_SQUIRE_UPLOAD, "Uploaded through Squire"),
            (CONNECTION_MANUAL, "Added manually in backend"),
        ],
    )  # Defines how the connection occured

    class Meta:
        # Set the default permissions. Each item has a couple of additional default permissions
        default_permissions = (
            "add",
            "change",
            "delete",
            "view",
            "sync",
        )
        unique_together = [["slug", "folder"], ["file_name", "folder"]]

    def __init__(self, *args, **kwargs):
        super(SquireNextCloudFile, self).__init__(*args, **kwargs)
        if self.id:
            self.file = NextCloudFile(path=self.path)

    def save(self, **kwargs):
        if self.file and (self.file_name == "" or self.file_name is None):
            self.file_name = self.file.name
            update_fields: set = kwargs.get("update_fields")
            if update_fields is not None and "file" in update_fields:
                kwargs["update_fields"].add("file_name")

        # Cleaning is not guaranteed when saving
        self._set_slug()

        return super(SquireNextCloudFile, self).save(**kwargs)

    def clean(self):
        self._set_slug()
        if self.file is None and (self.file_name is None or self.file_name == ""):
            raise ValidationError("Either file or filename should be defined", code="no_file_name_linked")

        # if SquireNextCloudFile.objects.filter(folder=self.folder, slug=self.slug).exclude(id=self.id).exists():
        #     raise ValidationError("A file with this name already exists in this folder.",code='duplicate_slug')

    def _set_slug(self):
        if self.slug is None or self.slug == "":
            self.slug = slugify(self.display_name)

    def exists_on_nextcloud(self):
        """Checks whether the folder exists on the nextcloud"""
        client = construct_client()
        return client.exists(self.file)

    def __str__(self):
        return f"File: {self.display_name}"

    @property
    def path(self):
        return f"{self.folder.path}{self.file_name}"

    def get_absolute_url(self):
        return reverse(
            "nextcloud:file_dl",
            kwargs={
                "folder_slug": self.folder.slug,
                "file_slug": self.slug,
            },
        )

    def get_file_type(self):
        return get_file_type(self.file_name)
