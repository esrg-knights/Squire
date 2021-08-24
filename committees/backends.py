from django.contrib.auth.models import Permission

from membership_file.util import user_to_member
from membership_file.models import Member


class AssociationGroupAuthBackend:

    def has_perm(self, user_obj, perm, obj=None):
        member = user_to_member(user_obj).get_member()
        if member is None:
            return False
        if not user_obj.is_active:
            return False

        app_label, codename = perm.split('.')

        return Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
            group__associationgroup__members__in=[member],
        ).exists()






