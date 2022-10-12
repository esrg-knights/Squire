


class NextCloudResource(object):
    def __init__(self, path, name=None):
        # Take the last bit with the name of the folder
        self.path = path
        if name:
            self.name = name
        else:
            self.name = path[max(0, path[:-1].rfind('/')):].replace('%20', ' ')


class NextCloudFile(NextCloudResource):
    def __init__(self, path, last_modified=None, content_type=None, **kwargs):
        super(NextCloudFile, self).__init__(path, **kwargs)
        self.last_modified = last_modified
        self.content_type = content_type

    def __str__(self):
        return f"File {self.name} of {self.content_type}"

    def file_type(self):
        return get_file_type(self.name)


class NextCloudFolder(NextCloudResource):

    def __init__(self, path, name=None):
        if name is None:
            name = path.split('/')[-1]
        super(NextCloudFolder, self).__init__(path, name=name)

    def __str__(self):
        return f'Folder: {self.name}'


class TextFileType:
    extension = ['txt', 'md']
    name = "Textfile"
    icon_class = "fas fa-file-alt"


class WordFileType:
    extension = ['doc', 'docx', 'odt']
    name = "Word file"
    icon_class = "fas fa-file-word"


class PDFFileType:
    extension = ['pdf',]
    name = "PDF file"
    icon_class = "fas fa-file-pdf"


class ImageFileType:
    extension = ['jpg', 'jpeg', 'png', 'gif']
    name = "Image file"
    icon_class = "fas fa-file-image"


class CompressedFileType:
    extension = ['zip', '7zip', 'rar']
    name = "Compressed files"
    icon_class = "fas fa-file-archive"


file_types = [TextFileType, WordFileType, PDFFileType, ImageFileType]


def get_file_type(file_name):
    extention = file_name.split('.')[-1]

    file_type_class = None

    for file_type in file_types:
        if extention in file_type.extension:
            file_type_class = file_type
            break

    if file_type_class:
        return file_type_class
    else:
        return None
