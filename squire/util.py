"""
Contains various utility functions.
"""

import os
import logging

def get_secret_key(filePath: str, enableMessages: bool = False) -> str:
    """
    Get the stored secret key from the filesystem.

    If this is the first time the program is run, create one.
    """

    try:
        secretfile = filePath
        with open(secretfile) as f:
            secret = f.read().strip()
    except FileNotFoundError:
        from django.core.management.utils import get_random_secret_key
        if enableMessages: #pragma: prod-msg
            print("Hello and welcome! I think that this is the first time you are" +
                " running me, I'm generating a new Secret Key for you to use. " +
                "Saving it to a file for next time...")
        secret = get_random_secret_key()
        with open(secretfile, 'w') as f:
            f.write(secret)
    return secret


def create_coverage_directory(directory: str, enableMessages: bool = False) -> None:
    '''
    Creates a folder and outputs a message if that folder did not exist before.
    @param directory The folder to create
    @param enableMessages Whether to print a message if the folder was created
    @post A folder with 'directory' as its filepath exists
          A message was printed if the folder was just created
    '''

    try:
        os.makedirs(directory)
        if enableMessages: #pragma: prod-msg
            print("Created a 'coverage'-folder since it did not yet exist! (" + directory + ") " +
                "Here, you will be able to find code-coverage reports after calling 'coverage run manage.py' " +
                "and 'coverage html' in that specific order.")
    except FileExistsError:
        # Directory already exists
        pass


def suppress_warnings(original_function):
    """
    Decorator that surpresses Django-warnings when calling a function.
    Useful for testcases where warnings are triggered on purpose and only
    clutter the command prompt.
    Source: https://stackoverflow.com/a/46079090
    """
    def new_function(*args, **kwargs):
        # raise logging level to ERROR
        logger = logging.getLogger('django.request')
        previous_logging_level = logger.getEffectiveLevel()
        logger.setLevel(logging.ERROR)

        # trigger original function that would throw warning
        original_function(*args, **kwargs)

        # lower logging level back to previous
        logger.setLevel(previous_logging_level)

    return new_function
