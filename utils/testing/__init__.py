from .form_test_util import FormValidityMixin

__all__ = ["FormValidityMixin", "return_boolean"]


def return_boolean(boolean=False):
    """Constructs a method that returns the given boolean. Useful for testing with given return values functions"""

    def return_function(*args, **kwargs):
        return boolean

    return return_function
