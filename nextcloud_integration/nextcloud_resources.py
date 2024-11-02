__all__ = ["NextCloudFile", "NextCloudFolder"]


class NextCloudResource(object):
    def __init__(self, path, name=None):
        # Take the last bit with the name of the folder
        self.path = path
        if name:
            self.name = name
        else:
            self.name = path[max(0, path[:-1].rfind("/")) :].replace("%20", " ")


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
            name = path.split("/")[-1]
        super(NextCloudFolder, self).__init__(path, name=name)

    def __str__(self):
        return f"Folder: {self.name}"


class AbstractFileType:
    name = "File"
    icon_class = "fas fa-file"


class TextFileType:
    extension = ["txt", "md"]
    name = "Text file"
    icon_class = "fas fa-file-alt"


class WordFileType:
    extension = ["doc", "docx", "odt"]
    name = "Word document"
    icon_class = "fas fa-file-word"


class PDFFileType:
    extension = [
        "pdf",
    ]
    name = "PDF file"
    icon_class = "fas fa-file-pdf"


class ImageFileType:
    extension = ["jpg", "jpeg", "png", "gif", "bmp"]
    name = "Image file"
    icon_class = "fas fa-file-image"


class CompressedFileType:
    extension = ["zip", "7zip", "rar"]
    name = "Compressed archive"
    icon_class = "fas fa-file-archive"


class PowerpointFileType:
    extension = ["ppt", "pptx", "odp"]
    name = "Powerpoint file"
    icon_class = "fas fa-file-powerpoint"


class ExcelFileType:
    extension = ["odx", "xls", "xlsx", "csv"]
    name = "Spreadsheet"
    icon_class = "fas fa-file-excel"


class CreativeFileType:
    extension = ["psd", "indd", "psb", "ai", "svg", "eps", "xcf"]
    name = "Creative file"
    icon_class = "fas fa-file-image"


file_types = [
    TextFileType,
    WordFileType,
    PDFFileType,
    ImageFileType,
    CompressedFileType,
    PowerpointFileType,
    ExcelFileType,
    CreativeFileType,
]


def get_file_type(file_name):
    extention = file_name.split(".")[-1]

    file_type_class = None

    for file_type in file_types:
        if extention in file_type.extension:
            file_type_class = file_type
            break

    if file_type_class:
        return file_type_class
    else:
        return AbstractFileType
