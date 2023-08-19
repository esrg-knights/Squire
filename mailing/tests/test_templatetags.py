from django.test import TestCase


from mailing.templatetags.mailing_tags import abs_url
from mailing.tests import CustomTestSite

class AbsUrlTestCase(TestCase):

    def setUp(self):
        self.context = {
            'site': CustomTestSite
        }

    def test_from_string(self):
        self.assertEqual(
            abs_url(self.context, "/local/url/", from_string=True),
            "https://test.com/local/url/"
        )

    def test_from_string_dash_insertion(self):
        self.assertEqual(
            abs_url(self.context, "local/url/", from_string=True),
            "https://test.com/local/url/"
        )

    def test_with_reverse(self):
        self.assertEqual(
            abs_url(self.context, "mailing:construct"),
            "https://test.com/mail/construct/"
        )

    def test_reverse_with_keywords(self):
        self.assertEqual(
            abs_url(self.context, "admin:auth_user_change", object_id=1),
            "https://test.com/admin/auth/user/1/change/"
        )
