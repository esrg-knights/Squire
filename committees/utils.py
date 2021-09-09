from django.contrib.auth.models import AnonymousUser
from membership_file.util import get_member_from_user


def user_in_association_group(user, association_group):
    """ Checks if the given user is part of the selected association_group """
    # Check standard Django group structure
    if isinstance(user, AnonymousUser):
        return False
    if association_group.site_group in user.groups.all():
        return True
        # Check Squire specific structure
    if get_member_from_user(user) in association_group.members.all():
        return True

    return False
