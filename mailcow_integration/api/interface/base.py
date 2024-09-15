from abc import ABC, abstractmethod
import logging
from typing import Any, Optional

logger = logging.getLogger("mailcow_api")


class MailcowAPIResponse(ABC):
    """Abstract base class for Mailcow API responses"""

    @classmethod
    def from_json_safe(cls, json: dict) -> Optional["MailcowAPIResponse"]:
        """Create a response object from a JSON response, or `None` if the JSON is invalid"""
        try:
            return cls.from_json(json)
        except TypeError as e:
            logger.warning(f"TypeError: {cls.__name__}.{e}")
        return None

    @classmethod
    @abstractmethod
    def from_json(cls, json: dict) -> "MailcowAPIResponse":
        """Create a response object from a JSON response"""
        raise NotImplementedError("Subclasses should define a `from_json` method")
