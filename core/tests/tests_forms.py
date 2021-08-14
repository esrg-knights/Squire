
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import CharField
from django.forms.models import model_to_dict
from django.test.testcases import TestCase
from django.utils.safestring import SafeText
from martor.fields import MartorFormField
from martor.widgets import MartorWidget

from core.fields import MarkdownObject, MarkdownCharField, MarkdownTextField
from core.forms import MarkdownForm
from core.models import MarkdownImage
from core.widgets import ImageUploadMartorWidget

User = get_user_model()


class DummyLogEntryMarkdownForm(MarkdownForm):
    """ Dummy Form to test MarkdownForm """
    class Meta:
        model = LogEntry
        fields = "__all__"
        widgets = {
            'object_repr': MartorWidget
        }
    updating_user_field_name = "user"

class MarkdownFormTest(TestCase):
    """
        Tests for MarkdownForm
    """
    def setUp(self):
        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.user = User.objects.create(username="test_user")
        self.obj = LogEntry.objects.create(user=self.user, action_flag=ADDITION, object_repr="My new object")
        self.content_type = ContentType.objects.get_for_model(LogEntry)

    def test_widget_changes(self):
        """ Tests if MartorWidgets are changed to ImageUploadMartorWidget """
        form = DummyLogEntryMarkdownForm(model_to_dict(self.obj), instance=self.obj, user=self.user)
        obj_repr_field = form['object_repr']
        self.assertIsNotNone(obj_repr_field)
        widget = obj_repr_field.field.widget
        self.assertIsNotNone(widget)
        self.assertIsInstance(widget, ImageUploadMartorWidget)

        # Correct widget params
        self.assertEqual(widget.content_type, self.content_type)
        self.assertEqual(widget.object_id, self.obj.id)

    def test_adopt_orphan_images_on_new_save(self):
        """
            Tests if uploaded images without an object-id are associated
            with a new model instance upon saving it
        """
        md_img_content_type = ContentType.objects.get_for_model(MarkdownImage)

        # Upload requests are tested elsewhere
        my_img = MarkdownImage.objects.create(content_type=self.content_type, uploader=self.user)
        other_img = MarkdownImage.objects.create(content_type=self.content_type, uploader=None)
        diff_img = MarkdownImage.objects.create(content_type=md_img_content_type, uploader=self.user)
        child_img = MarkdownImage.objects.create(content_type=self.content_type, uploader=self.user, object_id=123)

        form = DummyLogEntryMarkdownForm(model_to_dict(self.obj), instance=None, user=self.user)
        new_log = form.save()

        # Orphan MDImage must've changed. The others (not uploaded by user,
        # a different contenttype, or already attached) should not be modified
        self.assertEqual(MarkdownImage.objects.get(id=my_img.id).object_id, new_log.id)
        self.assertIsNone(MarkdownImage.objects.get(id=other_img.id).object_id)
        self.assertIsNone(MarkdownImage.objects.get(id=diff_img.id).object_id)
        self.assertEqual(MarkdownImage.objects.get(id=child_img.id).object_id, 123)

