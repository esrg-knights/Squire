from datetime import datetime

from django.core.validators import ValidationError
from django.test import TestCase, Client
from django.utils import timezone

from recurrence import Recurrence, deserialize as deserialize_recurrence_test

from activity_calendar.models import Activity



class TestCaseActivityClean(TestCase):
    fixtures = []

    def setUp(self):
        timezone.activate("Europe/Amsterdam")

        # Make an Activity
        self.base_activity_dict = {
            'title':        "Test Activity",
            'description':  "This is a testcase!\n\nWith a cool new line!",
            'location':     "In a testcase",
            'start_date':   timezone.get_current_timezone().localize(datetime(1970, 1, 1, 0, 0)),
            'end_date':     timezone.get_current_timezone().localize(datetime(1970, 1, 1, 23, 59)),
        }
        self.base_activity = Activity.objects.create(**self.base_activity_dict)

    def test_clean_valid(self):
        self.base_activity.title = "Updated!"
        self.base_activity.clean_fields()
    
    # Start date must be after end date
    def test_clean_wrong_start_date(self):
        self.base_activity.start_date = datetime(1971, 1, 1).astimezone(timezone.get_current_timezone())

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # Must have a recurrence rule if excluding dates
    def test_clean_exdate_no_rdate(self):
        self.base_activity.recurrences = deserialize_recurrence_test("EXDATE:19700101T230000Z")

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # Must do nothing if everything is defined correctly
    def test_clean_correct(self):
        self.base_activity.clean_fields()
