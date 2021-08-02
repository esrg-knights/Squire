from django.template.loader import get_template
from martor.widgets import AdminMartorWidget

class ImageUploadMartorWidget(AdminMartorWidget):
    """
        An AdminMartorWidget that also passes a ContentType and (possibly) ID
        of the model instance that is being edited or changed when an image is uploaded.
    """
    def __init__(self, content_type, object_id=None,
            placeholder=None, placeholder_detail_title="Placeholder Markdown", **kwargs):
        self.content_type = content_type
        self.object_id = object_id
        self.placeholder = placeholder
        self.placeholder_detail_title = placeholder_detail_title
        super().__init__(**kwargs)

    def render(self, name, value, attrs=None, renderer=None, **kwargs):
        assert self.content_type is not None

        widget = super().render(name, value, attrs, renderer, **kwargs)
        template = get_template('core/image_upload_editor.html')

        return template.render({
            'widget': widget,
            'content_type': self.content_type.id,
            'object_id': self.object_id,
            'placeholder': self.placeholder,
            'placeholder_detail_title': self.placeholder_detail_title,
        })
