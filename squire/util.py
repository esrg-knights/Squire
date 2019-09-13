"""
Contains various utility functions for settings.py.
"""

import os

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
