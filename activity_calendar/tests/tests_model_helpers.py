from django.test import TestCase

from activity_calendar.models import Activity, ActivityMoment, ActivitySlot, Participant

from django.contrib.auth import get_user_model

User = get_user_model()

##################################################################################
# Test the Activity and related models' helper methods
# @since 29 AUG 2020
##################################################################################


class ActivityRelatedModelHelpersTest(TestCase):
    fixtures = ["test_users.json"]

    def setUp(self):
        self.activity = Activity(id=4, title="Wow")
        self.activitymoment = ActivityMoment(id=1, parent_activity=self.activity)
        self.slot = ActivitySlot(id=1, parent_activitymoment=self.activitymoment, title="Wow2")

    # Tests the display method of Activity
    def test_activity_display(self):
        self.assertEqual(str(self.activity), "Wow (not recurring)")

    # Tests the display method of ActivitySlot
    def test_activityslot_display(self):
        self.assertEqual(str(self.slot), "Wow2")

    # Tests the display method of a Participant
    def test_participant_display(self):
        participant = Participant(activity_slot=self.slot, user=User.objects.filter(username="test_user").first())
        self.assertEqual(str(participant), str(participant.user))
