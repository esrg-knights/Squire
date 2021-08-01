import datetime

from django.utils import timezone

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################

def mock_now():
    dt = datetime.datetime(2020, 8, 14, 0, 0)
    return timezone.make_aware(dt)
