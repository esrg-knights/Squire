import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from core.pin_models import Pin, PinManager

User = get_user_model()


from .models import BlogCommentPinVisualiser, BlogPost, BlogComment


class PinManagerBasicTest(TestCase):
    """
        Tests related to the PinManager for Pins that do not
        have models attached to them.
    """
    fixtures = ['core/pins/blog_pins.json', 'test_users.json']

    def mock_now():
        return datetime.datetime(year=2022, month=3, day=1, hour=12, tzinfo=timezone.utc)

    def setUp(self):
        self.pin_1: Pin = Pin.objects.get(id=1)
        self.pin_2: Pin = Pin.objects.get(id=2)

        self.user = User.objects.get(username='test_user')

        self.pinmanager = PinManager()

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_all_pins(self, mock_now):
        """ Tests if pins are visible if they are published, not expired, and not members-only """
        pins = self.pinmanager.for_user(user=self.user)

        # All pins should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertIn(self.pin_2, pins)
        self.assertEqual(len(pins), 2)

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_queryset_used(self, mock_now):
        """ Tests if an alternative queryset is used if it is passed as a parameter """
        queryset = Pin.objects.filter(id=1)
        pins = self.pinmanager.for_user(user=self.user, queryset=queryset)

        # Only a single pin should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertEqual(len(pins), 1)

    def _test_pin2_only_accessible_with_perm(self, perms, pin_2_kwargs):
        """
            Tests if `self.pin_2` is only accessible for users with the given
            permission(s), and that `self.pin_1` is always accessible regardless
            of permissions.
        """
        # Update the pin with the new values
        Pin.objects.filter(id=self.pin_2.id).update(**pin_2_kwargs)

        # Pin 2 is not accessible without the permission
        pins = self.pinmanager.for_user(user=self.user)

        # All pins should be accessible
        self.assertIn(self.pin_1, pins)
        self.assertNotIn(self.pin_2, pins)
        self.assertEqual(len(pins), 1)

        # Pin 2 is accessible with the permission
        self.user.user_permissions.add(perms)
        self.user = User.objects.get(id=self.user.id) # Force the permission cache to reload
        pins = self.pinmanager.for_user(user=self.user)

        self.assertIn(self.pin_1, pins)
        self.assertIn(self.pin_2, pins)
        self.assertEqual(len(pins), 2)


    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_members_only(self, mock_now):
        """ Tests if pins are visible if they are members-only and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_members_only_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'is_members_only': True
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_not_published(self, mock_now):
        """ Tests if pins are visible if they are not published and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_future_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_publish_date': None
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_future_publish(self, mock_now):
        """ Tests if pins are visible if they publish in the future and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_future_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_publish_date': datetime.datetime(year=2030, month=1, day=1, tzinfo=timezone.utc)
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_pin_past_expiry(self, mock_now):
        """ Tests if pins are visible if they are expired and the user has the permissions """
        perm = Permission.objects.get(codename='can_view_expired_pins')
        self._test_pin2_only_accessible_with_perm(perm, {
            'local_expiry_date': datetime.datetime(year=1970, month=1, day=1, tzinfo=timezone.utc)
        })

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_highlights_only(self, _):
        """ Tests if limit_to_highlights is properly considered """
        self.pin_1.highlight_duration = datetime.timedelta(days=7)
        self.pin_2.highlight_duration = datetime.timedelta(days=365)
        self.pin_1.save()
        self.pin_2.save()

        pins = self.pinmanager.for_user(user=self.user, limit_to_highlights=True)

        # Only pin 2 is still highlighted. Pin 1's publish_date + highlight_duration < now
        self.assertNotIn(self.pin_1, pins)
        self.assertIn(self.pin_2, pins)
        self.assertEqual(len(pins), 1)


class PinVisualiserTest(TestCase):
    """ Tests whether overrides for `pin_foo_field`, `get_pin_foo`, and `pin_foo_query_fields` are used """

    fixtures = ['core/pins/blog_pins.json', 'test_users.json']

    def mock_now():
        return datetime.datetime(year=2022, month=3, day=1, hour=12, tzinfo=timezone.utc)

    def setUp(self):
        self.pin: Pin = Pin.objects.get(id=1)
        self.pinnable = BlogComment.objects.get(id=1)
        self.pin.content_object = self.pinnable
        self.pin.save()

        self.user = User.objects.get(username='test_user')

        self.pinmanager = PinManager()

    def test_model_field(self):
        """ Tests if a model field can be used in `pin_foo_field` """
        self.assertEqual(self.pin.description, self.pinnable.content)

    def test_model_property(self):
        """ Tests if a property can be used in `pin_foo_field` """
        self.assertEqual(self.pin.url, self.pinnable.url)

    def test_model_method_overridden(self):
        """ Tests if overrides for `get_pin_foo` are used """
        self.assertEqual(self.pin.title, f"Comment on {self.pinnable.blog_post.title}")

    def test_empty(self):
        """ Tests whether None is returned if nothing is overridden """
        self.assertIsNone(self.pin.expiry_date)


    def _get_test_query(self, query_fields):
        """ Obtains the resulting pin annotated with the result of pin_foo_query_fields """
        pin = Pin.objects.filter(id=self.pin.id).annotate(
            res=self.pinmanager._get_pin_field_query(BlogComment, 'local_expiry_date', query_fields)
        ).first()

        self.assertIsNotNone(pin)
        return pin

    def test_lookup_query(self):
        """ Tests if fields with foriegn key lookups are permitted (e.g. `blog_post__title`) """
        pin = self._get_test_query(BlogCommentPinVisualiser.pin_date_query_fields)
        self.assertEqual(pin.res, self.pinnable.blog_post.for_date)

    def test_multiple_fields(self):
        """ Tests if the first non-null value of the passed fields is returned """
        # Use blog's publish date because the comment publish date is empty
        pin = self._get_test_query(BlogCommentPinVisualiser.pin_publish_query_fields)
        self.assertEqual(pin.res, self.pinnable.blog_post.publishes_on)

        # Use comment's publish date because it's set
        self.pinnable.publish_date = timezone.datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.pinnable.save()
        pin = self._get_test_query(BlogCommentPinVisualiser.pin_publish_query_fields)
        self.assertEqual(pin.res, self.pinnable.publish_date)

    def test_no_fields(self):
        """ Tests if None is returned if there are no fields """
        pin = self._get_test_query(BlogCommentPinVisualiser.pin_expiry_query_fields)
        self.assertIsNone(pin.res)

    def test_local_override(self):
        """ Tests if local overrides are returned if they're not null """
        self.pin.local_expiry_date = timezone.datetime(2090, 1, 1, tzinfo=timezone.utc)
        self.pin.save()

        pin = self._get_test_query(BlogCommentPinVisualiser.pin_publish_query_fields)
        self.assertEqual(pin.res, self.pin.local_expiry_date)
