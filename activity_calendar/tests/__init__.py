import datetime

from django.utils import timezone


def mock_now(dt=None):
    """Script that changes the default now time to a preset value"""
    if dt is None:
        dt = datetime.datetime(2020, 8, 11, 0, 0)

    def adjust_now_time():
        return timezone.make_aware(dt)

    return adjust_now_time


def mock_is_organiser(result=True):
    """Script that replaces the is_organiser method returning the initial input of this method (default=True)"""

    def raise_fake_error(*args):
        return result

    return raise_fake_error
