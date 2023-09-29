from django.test import TestCase, RequestFactory
from core.views import LinkedLoginView


class LinkedLoginTestCase(TestCase):
    """Tests for LinkedLoginView"""

    class DummyLinkedLoginView(LinkedLoginView):
        """Linked login with some overrides"""

        image_source = "image.png"
        image_alt = "Image"
        link_title = "Link account"
        link_description = "Links account to something"
        link_extra = "Some extra info"

    view_class = DummyLinkedLoginView

    def setUp(self) -> None:
        self.view = self.view_class()
        request_factory = RequestFactory()
        self.view.setup(request_factory.get(f"/my_path/"))

        return super().setUp()

    def test_helper_methods(self):
        """Tests helper methods to retrieve class variables"""
        self.assertEqual(self.view.get_image_source(), self.view_class.image_source)
        self.assertEqual(self.view.get_image_alt(), self.view_class.image_alt)
        self.assertEqual(self.view.get_link_title(), self.view_class.link_title)
        self.assertEqual(self.view.get_link_description(), self.view_class.link_description)
        self.assertEqual(self.view.get_link_extra(), self.view_class.link_extra)

    def test_context(self):
        """Tests if context variables are passed"""
        context = self.view.get_context_data()
        self.assertIn("image_source", context)
        self.assertIn("image_alt", context)
        self.assertIn("link_title", context)
        self.assertIn("link_description", context)
        self.assertIn("link_extra", context)
