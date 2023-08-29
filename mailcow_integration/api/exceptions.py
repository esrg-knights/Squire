class MailcowException(Exception):
    """General exception class for errors raised by the Mailcow API"""


class MailcowAuthException(MailcowException):
    """Raised if authentication with the Mailcow server fails (invalid API key)"""


class MailcowAPIAccessDenied(MailcowException):
    """Raised if API access is denied for some IP"""


class MailcowAPIReadWriteAccessDenied(MailcowAPIAccessDenied):
    """Raised if API read/write access is denied (only read access is granted)"""


class MailcowRouteNotFoundException(MailcowException):
    """Invalid API route"""


class MailcowIDNotFoundException(MailcowRouteNotFoundException):
    """Invalid ID passed to an otherwise valid route"""
