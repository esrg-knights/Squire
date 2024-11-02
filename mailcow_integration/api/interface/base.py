from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Optional, Set, Tuple

logger = logging.getLogger("mailcow_api")


class MailcowAPIResponse(ABC):
    """Abstract base class for Mailcow API responses"""

    _cleanable_bools: Tuple[str, ...] = ()
    _cleanable_strings: Tuple[str, ...] = ()
    _cleanable_ints: Tuple[str, ...] = ()
    _cleanable_datetimes: Tuple[str, ...] = ()

    @classmethod
    def _issue_warning(cls, fieldname: str, value, parse_value=""):
        """Writes a warning about field parsing"""
        msg = f"JSONParseError in {cls.__name__}: Missing required field <{fieldname}>"
        if value is not None:
            msg = f"JSONParseError in {cls.__name__}: Field <{fieldname}> value could not be parsed as {parse_value}: <{value}>"
        logger.warning(msg)

    @classmethod
    def _issue_extra_warning(cls, fieldname: str, value):
        """Writes a warning about extra fields"""
        logger.warning(f"JSONParseError in {cls.__name__}: Found extra field <{fieldname}> with value <{value}>")

    @classmethod
    def _parse_as_bool(cls, fieldname: str, json: dict, default=None) -> Optional[bool]:
        """Parse a field from JSON as a boolean, or issue a warning"""
        val = json.get(fieldname, None)
        if val in ("0", "1"):
            # Sometimes booleans are returned as "0"/"1"
            return val == "1"
        elif isinstance(val, bool) or val in (0, 1):
            # Booleans sometimes returned as True/False, sometimes as 0/1
            return bool(val)
        cls._issue_warning(fieldname, val, "bool")
        return default

    @classmethod
    def _parse_as_string(cls, fieldname: str, json: dict, default=None) -> Optional[str]:
        """Parse a field from JSON as a string, or issue a warning"""
        val = json.get(fieldname, None)
        if val is not None:
            return str(val)
        cls._issue_warning(fieldname, val, "string")
        return default

    @classmethod
    def _parse_as_int(cls, fieldname: str, json: dict, default=None) -> Optional[int]:
        """Parse a field from JSON as an int, or issue a warning"""
        val = json.get(fieldname, None)
        if isinstance(val, int):
            return val
        cls._issue_warning(fieldname, val, "int")
        return default

    @classmethod
    def _parse_as_dt(cls, fieldname: str, json: dict, default=None) -> Optional[datetime]:
        """Parse a field from JSON as a datetime, or issue a warning"""
        val = json.get(fieldname, None)
        try:
            # Datetimes are sometimes returned in ISO-format, sometimes as a timestamp, sometimes as "0"
            if val == "0" or isinstance(val, int):
                return None if str(val) == "0" else datetime.fromtimestamp(val)
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            cls._issue_warning(fieldname, val, "ISO-datetime")
            return default

    @classmethod
    def _parse_as_enum(cls, fieldname: str, json: dict, enum: Enum, default=None) -> Optional[Enum]:
        """Parse a field from JSON as an Enum, or issue a warning"""
        val = json.get(fieldname, None)
        try:
            return enum(val)
        except ValueError:
            cls._issue_warning(fieldname, val, f"{enum.__class__.__name__} (Enum)")
            return default

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] = None) -> dict:
        """
        Validates and removes invalidated fields from the JSON. By default this
        looks at the various `cls._cleanable_<foo>` fields, but custom behaviour
        can be implemented in subclasses by overriding this method.

        Issues warnings through this file's `logger` when additional fields are returned
        by the MailCow API, when fields are expected by Squire('s dataclass) but not returned
        by the Mailcow API, or when a value returned by the Mailcow API cannot be parsed in the
        expected format (e.g. a boolean but '3' was returned).

        :raise: `AttributeError` if the JSON cannot be serialized into a MailcowAPIResponse
            (e.g. critical data is missing or has the wrong format)
        """
        extra_keys = extra_keys or set()

        # Show warning for extra attributes
        extra_attrs = json.keys() - (
            set(cls._cleanable_bools)
            | set(cls._cleanable_strings)
            | set(cls._cleanable_ints)
            | set(cls._cleanable_datetimes)
            | extra_keys
        )

        for attr in extra_attrs:
            cls._issue_extra_warning(attr, json[attr])

        cleaned_data = {}
        # Verify boolean fields
        for bool_field in cls._cleanable_bools:
            if (val := cls._parse_as_bool(bool_field, json)) is not None:
                cleaned_data[bool_field] = val

        # Verify string fields
        for string_field in cls._cleanable_strings:
            if (val := cls._parse_as_string(string_field, json)) is not None:
                cleaned_data[string_field] = val

        # Verify int fields
        for int_field in cls._cleanable_ints:
            if (val := cls._parse_as_int(int_field, json)) is not None:
                cleaned_data[int_field] = val

        # Verify datetime fields
        for dt_field in cls._cleanable_datetimes:
            if (val := cls._parse_as_dt(dt_field, json)) is not None:
                cleaned_data[dt_field] = val

        return cleaned_data

    @classmethod
    def from_json(cls, json: dict):
        """Create an instance from a JSON response, or `None` if this was not possible"""
        try:
            json = cls.clean(json)
        except AttributeError:
            return None
        return cls(**json)
