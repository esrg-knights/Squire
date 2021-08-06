from django.conf import settings

from core.tests.util import TestAccountUser, check_http_response

##################################################################################
# Utility Methods for testcases related to the membership file
# @since 12 FEB 2020
##################################################################################

class TestMemberUser(TestAccountUser):
    instance = 'test_member'

    @classmethod
    def get_fixtures(cls):
        return super().get_fixtures() + ['test_members.json']


def check_http_response_with_member_redirect(test, url, http_method, **kwargs):
    """
    Tests whether an Member can access a given page, and whether a non-member
        is redirected to the not-a-member page when accessing that same page.
        Method has otherwise the same parameters as check_http_response

    :throws AssertionError: The member could not access the page,
                                or the non-member was not redirected to the login page.
    :returns:               A tuple of both responses (account user first).
    """
    return (
        check_http_response(test, url, http_method, squire_user=TestMemberUser,
            response_status=200, **kwargs),
        check_http_response(test, url, http_method, squire_user=TestAccountUser,
            response_status=200, redirect_url=settings.MEMBERSHIP_FAIL_URL, **kwargs)
    )

# Fills the keys of one dictionary with those of another
# @param toFill The dictionary to fill
# @param fillData The dictionary whose data to use to fill empty
# @returns The values from fillData are in toFill
def fillDictKeys(toFill: dict, fillData: dict) -> dict:
    return {**toFill, **fillData}

# Gets the number of non-empty fields in a dictionary
# @param data The dictionary
# @returns the number of non-empty fields in a dictionary
def getNumNonEmptyFields(data: dict) -> int:
    count = 0
    for key in data:
        if data[key]:
            count += 1
    return count
