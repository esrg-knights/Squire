from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse_lazy

from utils.testing.view_test_utils import ViewValidityMixin


class TestCatalogueInstructions(ViewValidityMixin, TestCase):
    fixtures = ['test_users']
    base_url = reverse_lazy("mailing:construct")

    def test_authorised_get(self):
        self.client.force_login(User.objects.filter(is_superuser=True).first())
        self.assertValidGetResponse()

    def test_not_authorised_get(self):
        self.client.force_login(User.objects.filter(is_superuser=False).first())
        self.assertPermissionDenied()
