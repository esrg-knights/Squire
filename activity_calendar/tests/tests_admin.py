from django.test import TestCase, Client
from django.conf import settings

from activity_calendar.models import ActivitySlot, Activity
from core.models import ExtendedUser as User

##################################################################################
# Test cases for the activty admin panel
# @since 29 AUG 2020
##################################################################################

# Tests for the Admin Panel
class ActivityAdminTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_recurrence_dst.json']

    @classmethod
    def setUpTestData(self):
        activity = Activity.objects.all().first()
        slot = ActivitySlot(title="slot title", parent_activity=activity, recurrence_id=activity.start_date)
        slot.save()

    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.filter(username='test_admin').first())
    
    # Tests whether we can reach the activity page in the admin panel
    def test_activity_page(self):

        # General activity page
        response = self.client.get('/admin/activity_calendar/activity/', data={})
        self.assertEqual(response.status_code, 200)

        # Specific activity page
        response = self.client.get('/admin/activity_calendar/activity/1/change/', data={})
        self.assertEqual(response.status_code, 200)

    # Tests whether we can reach the activity slot page in the admin panel
    def test_slot_page(self):
        
        # General activity page
        response = self.client.get('/admin/activity_calendar/activityslot/', data={})
        self.assertEqual(response.status_code, 200)

        # Specific activity page
        response = self.client.get('/admin/activity_calendar/activityslot/1/change/', data={})
        self.assertEqual(response.status_code, 200)
