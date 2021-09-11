from django.test import TestCase

from core.tests.util import check_http_response, TestPublicUser


class TestActivityCalendarFrontEndViews(TestCase):

    # Calendar page should be accessible
    def test_public_calendar(self):
        check_http_response(self, '/activities/calendar/', 'get', TestPublicUser)



