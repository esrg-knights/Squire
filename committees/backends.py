from django.contrib.auth.models import Permission

from membership_file.util import get_member_from_user


class AssociationGroupAuthBackend:

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated:
            return False

        member = get_member_from_user(user_obj)
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

    def authenticate(self, *args, **kwargs):
        # This backend does not support authentication, but this method is called regardless, so return None instead
        return None






