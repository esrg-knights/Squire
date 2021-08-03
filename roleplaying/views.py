import os

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import Http404, FileResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.text import slugify
from django.views.generic import ListView, View, DetailView
from django.views.generic.edit import FormView, UpdateView, CreateView

from committees.views import GroupMixin
from utils.views import SearchFormMixin
from membership_file.views import MembershipRequiredMixin

from roleplaying.models import RoleplayingItem, RoleplayingSystem


class RoleplaySystemView(ListView):
    template_name = "roleplaying/system_overview.html"
    context_object_name = 'roleplay_systems'
    model = RoleplayingSystem

    paginate_by = 10


class SystemDetailView(MembershipRequiredMixin, DetailView):
    template_name = "roleplaying/system_details.html"
    model = RoleplayingSystem
    pk_url_kwarg = 'system_id'
    context_object_name = 'system'


class RoleplayingItemMixin:
    roleplay_item = None

    def dispatch(self, request, *args, **kwargs):
        self.roleplay_item = get_object_or_404(RoleplayingItem, id=kwargs.get('item_id', None))
        return super(RoleplayingItemMixin, self).dispatch(request, *args, **kwargs)


class DownloadDigitalItemView(MembershipRequiredMixin, RoleplayingItemMixin, View):
    http_method_names = ['get']

    def get(self, *args, **kwargs):
        if not self.roleplay_item.digital_version:
            raise Http404()

        # If no file name is given, set it to the item name
        filename = self.roleplay_item.digital_version_file_name
        if filename == "" or filename is None:
            filename = slugify(self.roleplay_item.name)

        # Assure the correct extention
        filename, _ = os.path.splitext(filename)
        _, extension = os.path.splitext(self.roleplay_item.digital_version.name)

        # file = open(self.roleplay_item.digital_version.url, 'rb')
        response = FileResponse(self.roleplay_item.digital_version)
        response['Content-Disposition'] = f'attachment; filename={filename}{extension}'

        return response
