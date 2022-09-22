from django.forms import Form, ValidationError
from django.forms.fields import CharField, ChoiceField


from nextcloud_integration.nextcloud_client import construct_client, OperationFailed
from nextcloud_integration.nextcloud_resources import NextCloudFile, NextCloudFolder


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
