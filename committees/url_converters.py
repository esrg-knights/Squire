from committees.models import AssociationGroup


class AssociationgroupConverter:
    regex = "[0-9]*"

    def to_python(self, value):
        try:
            return AssociationGroup.objects.get(id=value)
        except AssociationGroup.DoesNotExist:
            raise ValueError("There is no Associationgroup for id " + str(value))

    def to_url(self, association_group):
        # Make sure id values still work for old versions
        if isinstance(association_group, int):
            return association_group

        assert isinstance(association_group, AssociationGroup)
        return association_group.id
