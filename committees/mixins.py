from django.core.exceptions import PermissionDenied
from django.views.generic import FormView
from django.urls import reverse
from django.shortcuts import get_object_or_404

from utils.viewcollectives import *

from committees.models import AssociationGroup


def _wrap_association_group_for_context(association_group: AssociationGroup):
    """ Update the association_group with template optimised attributes """
    for group_type in AssociationGroup.GROUPTYPES:
        # Allow the type to be retrieved by selecting the type constant (e.g. association_group.GUILD)
        setattr(
            association_group,
            group_type[1].upper(),
            association_group.type == group_type[0]
        )
    return association_group


class AssociationGroupMixin(ViewCollectiveViewMixin):
    """ Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group """
    association_group = None
    selected_tab_name = None

    def setup(self, request, *args, group_id, **kwargs):
        self.association_group = group_id
        return super(AssociationGroupMixin, self).setup(request, *args, **kwargs)

    def _get_other_check_kwargs(self):
        """
        Returns a dict with other kwargs for validation checks (e.g. association_group)
        :return:
        """
        return {
            'association_group': self.association_group
        }

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupMixin, self).get_context_data(**kwargs)
        context['association_group'] = _wrap_association_group_for_context(self.association_group)
        context['config'] = self.config
        return context

    def _get_tab_url(self, url_name, **url_kwargs):
        """ Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        url_kwargs['group_id'] = self.association_group
        return super(AssociationGroupMixin, self)._get_tab_url(url_name, **url_kwargs)


class GroupSettingsMixin(AssociationGroupMixin):
    settings_option = None

    def setup(self, request, *args, **kwargs):
        super(GroupSettingsMixin, self).setup(request, *args, **kwargs)
        if not self.check_setting_access():
            raise PermissionDenied

    def check_setting_access(self):
        return self.settings_option.check_option_access(self.association_group)

    def get_context_data(self, **kwargs):
        options = sorted(
            self.config.get_options(self.association_group),
            key= lambda option: option.name)

        context = super(GroupSettingsMixin, self).get_context_data(**kwargs)
        context['settings_option'] = self.settings_option
        context['options_list'] = options
        return context


class BaseSettingsUpdateView(GroupSettingsMixin, FormView):
    template_name = "committees/committee_pages/group_settings_edit.html"

    def get_form_kwargs(self):
        form_kwargs = super(BaseSettingsUpdateView, self).get_form_kwargs()
        form_kwargs['instance'] = self.association_group
        return form_kwargs

    def form_valid(self, form):
        form.save()
        return super(BaseSettingsUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('committees:settings:settings_home', kwargs={'group_id': self.association_group})
