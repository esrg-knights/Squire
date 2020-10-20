import datetime

from urllib.parse import quote, unquote

from django.utils import timezone


from django.utils import dateparse


class DateTimeIsoConverter:
    regex = '[A-Z,0-9:+%-]*'

    # Note, quote and unquote change the string between iso string and valid url (without : and +)

    def to_python(self, value):
        return dateparse.parse_datetime(unquote(value))

    def to_url(self, datetime):
        assert datetime is datetime
        return quote(datetime.isoformat())
