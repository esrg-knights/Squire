import datetime

from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone, dateparse
from django.utils.http import urlencode
from unittest.mock import patch

from activity_calendar.models import ActivitySlot, Activity, Participant
from core.models import ExtendedUser as User
from core.util import suppress_warnings

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################

def mock_now():
    dt = datetime.datetime(2020, 8, 14, 0, 0)
    return timezone.make_aware(dt)
