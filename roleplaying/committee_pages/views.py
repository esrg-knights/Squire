from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import TemplateView,  FormView

from utils.views import PostOnlyFormViewMixin

from committees.committeecollective import AssociationGroupMixin
from committees.forms import AssociationGroupUpdateForm, AddOrUpdateExternalUrlForm, \
    DeleteGroupExternalUrlForm, AssociationGroupMembershipForm




class CampaignDetailView(AssociationGroupMixin, TemplateView):
    template_name = "committees/committee_pages/group_detail_info.html"


