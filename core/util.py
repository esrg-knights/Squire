import logging

from enum import Enum
from functools import wraps

"""
Contains various utility functions for the whole application.
"""

# An enumeration that allows comparison
# See: https://docs.python.org/3/library/enum.html#orderedenum
class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

def suppress_warnings(function=None, logger_name='django.request'):
    """
    Decorator that surpresses Django-warnings when calling a function.
    Useful for testcases where warnings are triggered on purpose and only
    clutter the command prompt.
    Source: https://stackoverflow.com/a/46079090
    """
    def decorator(original_func):
        @wraps(original_func)
        def _wrapped_view(*args, **kwargs):
            # raise logging level to ERROR
            logger = logging.getLogger(logger_name)
            previous_logging_level = logger.getEffectiveLevel()
            logger.setLevel(logging.ERROR)

            # trigger original function that would throw warning
            original_func(*args, **kwargs)

            # lower logging level back to previous
            logger.setLevel(previous_logging_level)
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator
