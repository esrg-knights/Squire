


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



class NextCloudFolder(NextCloudResource):

    def __init__(self, path, name=None):
        if name is None:
            name = path.split('/')[-1]
        super(NextCloudFolder, self).__init__(path, name=name)

    def __str__(self):
        return f'Folder: {self.name}'
