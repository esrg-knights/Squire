import os

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import ListView, View, DetailView, UpdateView

from utils.views import SearchFormMixin
from membership_file.views import MembershipRequiredMixin

from roleplaying.forms import RoleplayingSystemUpdateForm
from roleplaying.models import RoleplayingItem, RoleplayingSystem


class RoleplaySystemView(SearchFormMixin, ListView):
    template_name = "roleplaying/system_overview.html"
    context_object_name = 'roleplay_systems'
    filter_field_name = "name"
    model = RoleplayingSystem

    paginate_by = 10

    def get_queryset(self):
        return super(RoleplaySystemView, self).get_queryset().filter(is_public=True)

    def get_context_data(self, **kwargs):
        context = super(RoleplaySystemView, self).get_context_data(**kwargs)
        context.update({
            'item_type': ContentType.objects.get_for_model(RoleplayingItem),
        })
        return context


class SystemDetailView(MembershipRequiredMixin, DetailView):
    template_name = "roleplaying/system_details.html"
    model = RoleplayingSystem
    pk_url_kwarg = 'system_id'
    context_object_name = 'system'

    def get_context_data(self, **kwargs):
        item_type = ContentType.objects.get_for_model(RoleplayingItem)
        item_class_name = slugify(item_type.model_class().__name__)

        context = super(SystemDetailView, self).get_context_data(**kwargs)
        system = context['system']
        context.update({
            'item_type': item_type,
            'can_maintain_ownership': self.request.user.has_perm(f'roleplaying.maintain_ownerships_for_{item_class_name}'),
            'owned_items': system.items.get_all_in_possession(),
        })
        return context


class SystemUpdateView(MembershipRequiredMixin, PermissionRequiredMixin, UpdateView):
    template_name = "roleplaying/system_update.html"
    form_class = RoleplayingSystemUpdateForm
    model = RoleplayingSystem
    pk_url_kwarg = 'system_id'
    permission_required = 'roleplaying.change_roleplayingsystem'
    context_object_name = 'system'

    def form_valid(self, form):
        messages.success(self.request, f"{self.object.name} has been updated")
        return super(SystemUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse("roleplaying:system_details", kwargs={'system_id': self.object.id,})


class RoleplayingItemMixin:
    roleplay_item = None

    def dispatch(self, request, *args, **kwargs):
        self.roleplay_item = get_object_or_404(RoleplayingItem, id=kwargs.get('item_id', None))
        return super(RoleplayingItemMixin, self).dispatch(request, *args, **kwargs)


class DownloadDigitalItemView(MembershipRequiredMixin, RoleplayingItemMixin, View):
    http_method_names = ['get']

    def get(self, *args, **kwargs):
        if not self.roleplay_item.local_file:
            raise Http404()

        # If no file name is given, set it to the item name
        filename = self.roleplay_item.local_file_name
        if filename == "" or filename is None:
            filename = slugify(self.roleplay_item.name)

        # Assure the correct extention
        filename, _ = os.path.splitext(filename)
        _, extension = os.path.splitext(self.roleplay_item.local_file.name)

        # file = open(self.roleplay_item.digital_version.url, 'rb')
        response = FileResponse(self.roleplay_item.local_file)
        response['Content-Disposition'] = f'attachment; filename={filename}{extension}'

        return response
