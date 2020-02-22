from django.test import TestCase
from django.conf import settings
from . import util

import os

##################################################################################
# Test cases for util.py
# @since 14 AUG 2019
##################################################################################


# Tests the get_secret_key(..) method
class GetSecretKeyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.testcase_key_path = os.path.join(settings.BASE_DIR, 'test', 'input', 'testcase_secret_key.txt')
        cls.testcase_nonexisting_key_path = os.path.join(settings.BASE_DIR, 'test', 'input', 'testcase_nonexisting_secret_key.txt')

    # Tests if a file can be opened if it exists
    def test_get_when_exists(self):
        secret = util.get_secret_key(self.testcase_key_path, False)
        self.assertEqual(secret, 'abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmn')
    
    # Tests if a new file is created when it does not exist
    def test_get_when_not_exists(self):
        # Ensure the file does not already exist!
        if os.path.isfile(self.testcase_nonexisting_key_path):
            try: # If it does, try deleting it
                os.remove(self.testcase_nonexisting_key_path)
            except OSError as e: # If auto-deletion fails, notify the user and fail the test
                self.fail("The file " + self.testcase_nonexisting_key_path +" should not exist, but it did! Please delete it manually before running the tests again.")

        secret = util.get_secret_key(self.testcase_nonexisting_key_path, False)

        # Check that a key of the correct length got passed
        self.assertEqual(len(secret), 50)

        # Check that the key was created in a file
        self.assertTrue(os.path.isfile(self.testcase_nonexisting_key_path))

        try: # If it does, try deleting it
            os.remove(self.testcase_nonexisting_key_path)
        except OSError as e:
            pass
