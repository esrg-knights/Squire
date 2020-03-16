from django.test import TestCase
from django.conf import settings

from enum import Enum

from core.tests.util import checkAccessPermissions, PermissionLevel
from membership_file.models import Member
from membership_file.models import MemberUser as User

##################################################################################
# Utility Methods for testcases related to the membership file
# @since 12 FEB 2020
##################################################################################

# Enumeration that specifies member vs non-member status.
class PermissionType(Enum):
    TYPE_MEMBER = 1
    TYPE_NO_MEMBER = 2

# Checks whether a given url can be accessed with a given HTTP Method by a user with a given permissionType
# Invokes the checkAccessPermissions method from the Core app.
def checkAccessPermissionsMember(test: TestCase, url: str, httpMethod: str, permissionType: PermissionType,
        user: User = None, redirectUrl: str = "", data: dict = {}) -> None:
    
    member = None
    if permissionType == PermissionType.TYPE_MEMBER:
        # Requesting user should be a member
        member = Member.objects.get(email='linked_member@example.com')
        if user is None:
            user = User.objects.get(username='test_user')
        else:
            member = Member.objects.filter(user=user).first()
            if member is None:
                # The passed user was NOT yet a member, but should be one!
                member = Member.objects.get(email='linked_member@example.com')
                member.user = user
                member.save()
    else:
        # Requesting user should NOT be a member
        if user is None:
            user = User.objects.get(username='test_user_alt')
        else:
            member = Member.objects.filter(user=user).first()
            if member is not None:
                # The passed user was a member, but should NOT be one!
                member.user = None
                member.save()

    checkAccessPermissions(test, url, httpMethod, PermissionLevel.LEVEL_USER, user, redirectUrl, data)


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
