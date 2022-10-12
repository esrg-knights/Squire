from django.forms import Form, ValidationError, ModelForm
from django.forms.fields import CharField, ChoiceField
from django.utils.text import slugify

from nextcloud_integration.nextcloud_client import construct_client, OperationFailed
from nextcloud_integration.nextcloud_resources import NextCloudFile, NextCloudFolder
from nextcloud_integration.models import NCFolder, NCFile
from nextcloud_integration.widgets import NextcloudFileSelectWidget


class FileMoveForm(Form):
    directory_name = CharField(required=True, min_length=3, max_length=16)
    file_name = ChoiceField()

    def __init__(self, *args, local_path='', **kwargs):
        super(FileMoveForm, self).__init__(*args, **kwargs)
        self.local_path = local_path
        self.availlable_files = None
        self.fields['file_name'].choices = self.get_file_choices(recheck=True)

    def get_file_choices(self, recheck=False):
        if self.availlable_files is None or recheck:
            client = construct_client()
            availlable_files = client.ls(remote_path=self.local_path)
            self.availlable_files = list(filter(
                lambda nextcloud_resource:
                nextcloud_resource.__class__ == NextCloudFile,
                availlable_files
            ))

        return [(file.name, file.name) for file in self.availlable_files]


    def clean_directory_name(self):
        directory_name = self.cleaned_data['directory_name']
        if directory_name.startswith('/'):
            raise ValidationError("directory_name can not start with a /")
        return directory_name

    def execute(self):
        client = construct_client()
        folder_path = self.local_path + '/' + self.cleaned_data['directory_name']
        folder = NextCloudFolder(folder_path)

        if not client.exists(resource=folder):
            folder = client.mkdir(folder)

        file = next(file for file in self.availlable_files if file.name == self.cleaned_data['file_name'])

        client.mv(file, to_folder=folder)


class FolderCreateForm(ModelForm):
    class Meta:
        model = NCFolder
        fields = ["display_name", "description"]

    def clean(self):
        self.instance.path = f"/{slugify(self.cleaned_data['display_name'])}/"
        return super(FolderCreateForm, self).clean()


class SynchFileToFolderForm(ModelForm):
    selected_file = ChoiceField(widget=NextcloudFileSelectWidget())

    class Meta:
        model = NCFile
        fields = ["display_name", "description", "selected_file"]

    def __init__(self, *args, folder: NCFolder=None, **kwargs):
        assert folder is not None
        self.folder = folder
        self.file_list = self.get_unsynched_files()

        super(SynchFileToFolderForm, self).__init__(*args, **kwargs)
        self.instance.folder = self.folder
        self.fields["selected_file"].choices = [(file.name, file) for file in self.file_list]

    def save(self, commit=True):
        client = construct_client()
        # client.mv()


        file = next(file for file in self.file_list if file.name == self.cleaned_data["selected_file"])
        folder = self.folder.folder
        client.mv(file, folder)
        self.instance.file = file
        super(SynchFileToFolderForm, self).save(commit=commit)


    def get_unsynched_files(self):
        client = construct_client()
        return [x for x in client.ls() if isinstance(x, NextCloudFile)]

    def clean(self):
        self.instance.slug = slugify(self.cleaned_data['display_name'])
        return super(SynchFileToFolderForm, self).clean()
