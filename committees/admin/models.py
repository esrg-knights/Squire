from committees.models import AssociationGroup


class AssociationGroupPanelControl(AssociationGroup):
    """Class used by the admin to control group panel access"""

    class Meta:
        proxy = True
