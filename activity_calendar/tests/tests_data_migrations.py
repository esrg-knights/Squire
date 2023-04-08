from datetime import timedelta

from django.utils import dateparse
from django_test_migrations.contrib.unittest_case import MigratorTestCase
from recurrence import deserialize as deserialize_recurrence_test
from unittest import skip

from core.tests.util import suppress_warnings


@skip("Old data migration tests don't need to be run")
class ActivitySlotLinkToActivityMomentTest(MigratorTestCase):
    """
    ActivitySlots used to be linked to Activities (with a recurrence_id) directly, but
    this was changed to make them link to an ActivityMoment instead (getting rid of recurrence_id).
    This tests whether old ActivitySlots are migrated properly through the data migration.
    """

    migrate_from = ("activity_calendar", "0022_activity_display_end_time")
    migrate_to = ("activity_calendar", "0023_activityslot_link_to_activitymoment")

    @suppress_warnings(logger_name="activity_calendar.migrations.0018_activityslot_link_to_activitymoment")
    def setUp(self):
        return super().setUp()

    def prepare(self):
        """Prepare some data before the migration."""
        Activity = self.old_state.apps.get_model("activity_calendar", "Activity")
        ActivityMoment = self.old_state.apps.get_model("activity_calendar", "ActivityMoment")
        ActivitySlot = self.old_state.apps.get_model("activity_calendar", "ActivitySlot")

        self.start_1 = dateparse.parse_datetime("2022-01-03T18:00:00Z")
        self.start_2 = self.start_1 + timedelta(days=7)

        activity_data = {
            "title": "Boardgame Evening",
            "description": "Play Boardgames!",
            "location": "Online",
            "start_date": self.start_1,
            "end_date": dateparse.parse_datetime("2022-01-03T21:00:00Z"),
            "recurrences": deserialize_recurrence_test("RRULE:FREQ=WEEKLY;BYDAY=MO"),
        }
        activity = Activity.objects.create(id=1, **activity_data)
        activitymoment = ActivityMoment.objects.create(
            id=1, parent_activity=activity, recurrence_id=dateparse.parse_datetime("2022-01-03T18:00:00Z")
        )

        activityslot_with_activitymoment = ActivitySlot.objects.create(
            id=1, title="Has ActivityMoment", parent_activity=activity, recurrence_id=self.start_1
        )
        activityslot_without_activitymoment = ActivitySlot.objects.create(
            id=2, title="No ActivityMoment", parent_activity=activity, recurrence_id=self.start_2
        )
        activityslot_without_recurrence_id = ActivitySlot.objects.create(
            id=3, title="No recurrence_id", parent_activity=activity, recurrence_id=None
        )

        # 2nd activity
        activity_2 = Activity.objects.create(id=2, **activity_data)
        activityslot_different_activity_no_id = ActivitySlot.objects.create(
            id=4, title="xxx", parent_activity=activity_2, recurrence_id=None
        )
        activityslot_different_activity_id = ActivitySlot.objects.create(
            id=5, title="xxx", parent_activity=activity_2, recurrence_id=self.start_1
        )

    def test_migration_existing_activitymoment(self):
        """Tests if existing ActivityMoments are found"""
        ActivitySlot = self.new_state.apps.get_model("activity_calendar", "ActivitySlot")

        # ActivitySlot is linked to the existing activitymoment with a matching recurrence_id
        parent_activitymoment = ActivitySlot.objects.get(id=1).parent_activitymoment
        self.assertIsNotNone(parent_activitymoment)
        self.assertEqual(parent_activitymoment.parent_activity_id, 1)
        self.assertEqual(parent_activitymoment.recurrence_id, self.start_1)

    def test_migration_no_existing_activitymoment(self):
        """Tests if a new ActivityMoment is created"""
        ActivitySlot = self.new_state.apps.get_model("activity_calendar", "ActivitySlot")

        # ActivitySlot is linked to a new activitymoment with the correct recurrence_id
        parent_activitymoment = ActivitySlot.objects.get(id=2).parent_activitymoment
        self.assertIsNotNone(parent_activitymoment)
        self.assertNotEqual(parent_activitymoment.id, 1)
        self.assertEqual(parent_activitymoment.parent_activity_id, 1)
        self.assertEqual(parent_activitymoment.recurrence_id, self.start_2)

    def test_migration_no_recurrence_id(self):
        """Tests whether old slots without a recurrence_id are migrated"""
        ActivitySlot = self.new_state.apps.get_model("activity_calendar", "ActivitySlot")

        # ActivitySlot is linked to a new activitymoment with the correct recurrence_id
        parent_activitymoment = ActivitySlot.objects.get(id=3).parent_activitymoment
        self.assertIsNotNone(parent_activitymoment)
        self.assertEqual(parent_activitymoment.id, 1)
        self.assertEqual(parent_activitymoment.parent_activity_id, 1)
        self.assertEqual(parent_activitymoment.recurrence_id, self.start_1)

    def test_migration_no_interfere(self):
        """
        Tests whether existing ActivityMoments with a matching recurrence_id but
        for a different activity do not interfere.
        """
        ActivitySlot = self.new_state.apps.get_model("activity_calendar", "ActivitySlot")

        # ActivitySlots have a matching recurrence_id with another activity's ActivityMoment
        parent_activitymoment = ActivitySlot.objects.get(id=4).parent_activitymoment
        self.assertIsNotNone(parent_activitymoment)
        self.assertEqual(parent_activitymoment.parent_activity_id, 2)

        parent_activitymoment = ActivitySlot.objects.get(id=5).parent_activitymoment
        self.assertIsNotNone(parent_activitymoment)
        self.assertEqual(parent_activitymoment.parent_activity_id, 2)
