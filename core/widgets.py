from django.template.loader import get_template
from martor.widgets import AdminMartorWidget, get_theme

class ImageUploadMartorWidget(AdminMartorWidget):
    """
        An AdminMartorWidget that also passes a ContentType and (possibly) ID
        of the model instance that is being edited or changed when an image is uploaded.

        Also provides the option to provides placeholder-equivalent Markdown.
        :param content_type:    ContentType of the instance for which images can be uploaded.
        :param object_id:       ID of the instance for which images can be uploaded. When not
            passed, uploaded images will not be linked to any specific object of the passed
            ContentType.
        :param placeholder:     A string that is rendered in a <details>-element above the widget to
            function as a sort of placeholder. This string can contain markdown.
        :param placeholder_detail_title: The text in the <summary>-element of the placeholder. Can
            be left empty to not have a <summary>-element.
    """
    class Media:
        css = {
            'all': ('css/martor-placeholder.css',),
        }

    def __init__(self, content_type, object_id=None,
            placeholder=None, placeholder_detail_title=None, **kwargs):
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
