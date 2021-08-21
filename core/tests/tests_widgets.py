from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.testcases import TestCase

from core.fields import MarkdownObject
from core.widgets import ImageUploadMartorWidget

User = get_user_model()


class ImageUploadMartorWidgetTest(TestCase):
    """ Tests for a variant of Martor's widget that allows image uploads """
    def setUp(self):
        self.user = User.objects.create(username="test_user")

        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.obj = LogEntry.objects.create(user=self.user, action_flag=ADDITION, object_repr="My new object")
        self.content_type = ContentType.objects.get_for_model(LogEntry)

        self.widget = ImageUploadMartorWidget(self.content_type, self.obj.id)

    def test_no_placeholder_content(self):
        """ Tests if the placeholder is hidden if there's no content to display """
        self.widget.placeholder = None
        self.widget.placeholder_detail_title = "Cool title!"

        html = self.widget.render("markdown_field_name", "**markdown** content", attrs={})
        self.assertNotIn("Cool title!", html)
        self.assertNotIn('div class="md-placeholder"', html)
        self.assertIn("**markdown** content", html)

    def test_no_placeholder_title(self):
        """ Tests if the placeholder title is hidden if there's no title to display """
        self.widget.placeholder = MarkdownObject("placeholder _markdown_ text")
        self.widget.placeholder_detail_title = None

        html = self.widget.render("markdown_field_name", "**markdown** content", attrs={})
        self.assertNotIn("<i>click to expand/hide</i>", html)
        self.assertIn('div class="md-placeholder"', html)
        self.assertIn("**markdown** content", html)
        # Must have a rendered and raw variant
        self.assertIn("placeholder _markdown_ text", html)
        self.assertIn("placeholder <em>markdown</em> text", html)

    def test_hiddenfields_no_object_id(self):
        """ Tests if the hidden fields for image uploads are correctly set without an object-id """
        self.widget.object_id = None
        html = self.widget.render("markdown_field_name", "**markdown** content", attrs={})

        self.assertNotIn("martor-image-upload:id", html)
        self.assertIn("martor-image-upload:content_type", html)

    def test_hiddenfields_with_object_id(self):
        """ Tests if the hidden fields for image uploads are correctly set with an object-id """
        html = self.widget.render("markdown_field_name", "**markdown** content", attrs={})

        self.assertIn("martor-image-upload:id", html)
        self.assertIn("martor-image-upload:content_type", html)
