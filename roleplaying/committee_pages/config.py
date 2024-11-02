from committees.committee_pages.config import AssociationGroupHomeConfig
from committees.models import AssociationGroup

from roleplaying.committee_pages.views import CampaignDetailView


def filter_campaigns(association_group: AssociationGroup):
    return association_group.type == AssociationGroup.CAMPAIGN


AssociationGroupHomeConfig.add_filter(filter_campaigns, CampaignDetailView)
