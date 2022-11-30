from django.forms import Form, ValidationError, ModelForm
from django.forms.formsets import BaseFormSet
from django.forms.fields import CharField, ChoiceField, HiddenInput
from django.forms.renderers import get_default_renderer
from django.utils.text import slugify

from utils.forms import FormGroup

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
            raise ValidationError(
                "directory_name can not start with a /",
                code='invalid_directory_name',
            )
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
        self.instance.connection = "NcS"
        self.fields["selected_file"].choices = [(file.name, file) for file in self.file_list]

    def clean_selected_file(self):
        self.instance.file_name = self.cleaned_data["selected_file"]
        print(self.instance.file_name)
        return self.cleaned_data["selected_file"]


    def save(self, commit=True):
        client = construct_client()
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


class FolderEditForm(ModelForm):
    class Meta:
        model = NCFolder
        fields = ["display_name", "description", "requires_membership"]


class FileEditForm(ModelForm):
    id = HiddenInput()

    class Meta:
        model = NCFile
        fields = ["display_name", "description"]

    def __init__(self, *args, **kwargs):
        super(FileEditForm, self).__init__(*args, **kwargs)
        self.id = self.instance.id

    def clean_id(self):
        if self.instance.id != self.cleaned_data["id"]:
            raise ValidationError("File id is invalid", code="invalid_id")


class FileEditFormset(BaseFormSet):
    form = FileEditForm

    def __init__(self, *args, nc_files=None, **kwargs):
        assert nc_files is not None
        self.nc_files = nc_files
        # Initialising the form directly skips the factory, so set some base values requeired
        self.renderer = get_default_renderer()
        self.min_num = 0
        self.max_num = len(nc_files)
        self.absolute_max = self.max_num
        self.validate_min = self.max_num
        self.validate_max = self.max_num
        self.can_delete = False
        self.can_order = False

        super(FileEditFormset, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super(FileEditFormset, self).get_form_kwargs(index)
        kwargs["instance"] = self.nc_files[index]
        return kwargs

    def total_form_count(self):
        return len(self.nc_files)

    def save(self):
        for form in self.forms:
            form.save()

class FolderEditFormGroup(FormGroup):
    form_class = FolderEditForm
    formset_class = FileEditFormset

    def __init__(self, folder=None, **kwargs):
        self.folder = folder
        self.form_kwargs = {'instance': self.folder}
        self.formset_kwargs = {'FileEditFormset': {'nc_files': self.folder.files.all()}}
        super(FolderEditFormGroup, self).__init__(**kwargs)

    # def get_form_kwargs(self, form_class):
    #     kwargs = super(FolderEditFormGroup, self).get_form_kwargs(form_class)
    #     kwargs['instance'] = self.folder
    #     return kwargs

    # def get_formset_kwargs(self, formset_class):
    #     kwargs = super(FolderEditFormGroup, self).get_formset_kwargs(formset_class)
    #     kwargs['nc_files'] = self.folder.files.all()
    #     return kwargs



