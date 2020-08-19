from django.test import TestCase

from core.tests.util import checkAccessPermissions, PermissionLevel


# Create your tests here.
class TestCaseActivityCalendarFrontEndViews(TestCase):
    fixtures = []

    def test_public_calendar(self):
        checkAccessPermissions(self, '/calendar', 'get', PermissionLevel.LEVEL_PUBLIC)

    def test_old_google_calendar(self):
        checkAccessPermissions(self, '/calendar/google_html', 'get', PermissionLevel.LEVEL_PUBLIC)


    