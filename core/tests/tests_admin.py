from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from core.admin import MarkdownImageAdmin
from core.models import MarkdownImage

User = get_user_model()

@override_settings(MARKDOWN_IMAGE_MODELS=['core.markdownimage'])
class MarkdownImageAdminTest(TestCase):
    """
        Tests for the MarkdownImageAdmin ModelAdmin.
    """
    fixtures = ['test_users']

    def setUp(self):
        self.model_admin = MarkdownImageAdmin(model=MarkdownImage, admin_site=AdminSite())
        self.content_type = ContentType.objects.get_for_model(MarkdownImage)
        self.object_without_related = MarkdownImage.objects.create(content_type=self.content_type)
        self.object_with_related = MarkdownImage.objects.create(content_object=self.object_without_related)

    def test_contentobject(self):
        """ Tests if the related object (if any) can be clicked through a link """
        # Has a related object -> must provide a link
        column_str = self.model_admin.content_object(self.object_with_related)
        self.assertIn(reverse(f"admin:core_markdownimage_change", args=[self.object_without_related.id]), column_str)
        self.assertRegex(column_str, "target=._blank")

        # Does not have a related object -> no link
        column_str = self.model_admin.content_object(self.object_without_related)
        self.assertEqual(column_str, "-")

    def test_formfield_for_fk(self):
        """ Tests if the available ContentTypes are properly limited to those in the settings """
        # Limit selection of ContentTypes
        fk_content_types = self.model_admin.formfield_for_foreignkey(MarkdownImage.content_type.field, request=None)
        self.assertEqual(len(fk_content_types.queryset), 1)
        self.assertEqual(fk_content_types.queryset.first(), self.content_type)

        # Other selections are unaffected
        fk_users = self.model_admin.formfield_for_foreignkey(MarkdownImage.uploader.field, request=None)
        self.assertEqual(fk_users.queryset.count(), User.objects.all().count())

