from django.views.generic import TemplateView


from committees.mixins import AssociationGroupMixin


class CampaignDetailView(AssociationGroupMixin, TemplateView):
    template_name = "roleplaying/committees/roleplay_home.html"
