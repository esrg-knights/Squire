from datetime import datetime
import logging
from typing import Optional
from core.api_response import GenericAPIResponse


class MailcowAPIResponse(GenericAPIResponse):
    """Abstract base class for Mailcow API responses"""

    logger = logging.getLogger("mailcow_api")

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
