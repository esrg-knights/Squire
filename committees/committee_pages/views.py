from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from utils.views import PostOnlyFormViewMixin

from committees.mixins import AssociationGroupMixin, GroupSettingsMixin
from committees.forms import (
    AssociationGroupUpdateForm,
    AddOrUpdateExternalUrlForm,
    DeleteGroupExternalUrlForm,
    AssociationGroupMembershipForm,
)


__all__ = [
    "AssociationGroupDetailView",
    "AssociationGroupSettingsView",
    "AssociationGroupQuickLinksView",
    "AssociationGroupQuickLinksAddOrUpdateView",
    "AssociationGroupQuickLinksDeleteView",
    "AssociationGroupMembersView",
    "AssociationGroupMemberUpdateView",
]


class AssociationGroupDetailView(AssociationGroupMixin, TemplateView):
    template_name = "committees/committee_pages/group_detail_info.html"

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupDetailView, self).get_context_data(**kwargs)
        context["quicklinks_internal"] = self.construct_internal_links()
        context["quicklinks_external"] = self.association_group.shortcut_set.all()
        return context

    def construct_internal_links(self):
        """Loops over the configs to determine any quicklinks"""
        quicklinks = []
        for config in self.config.registry.get_applicable_configs(self.request, **self._get_other_check_kwargs()):
            quicklinks.extend(config.get_local_quicklinks(association_group=self.association_group))
        return quicklinks


class AssociationGroupSettingsView(GroupSettingsMixin, TemplateView):
    template_name = "committees/committee_pages/group_settings_home.html"
    settings = None

    def check_setting_access(self):
        return True


class AssociationGroupQuickLinksView(GroupSettingsMixin, TemplateView):
    template_name = "committees/committee_pages/group_detail_quicklinks.html"

    def get_context_data(self, **kwargs):
        return super(AssociationGroupQuickLinksView, self).get_context_data(
            form=AddOrUpdateExternalUrlForm(association_group=self.association_group), **kwargs
        )


class AssociationGroupQuickLinksAddOrUpdateView(GroupSettingsMixin, PostOnlyFormViewMixin, FormView):
    form_class = AddOrUpdateExternalUrlForm

    def get_form_kwargs(self):
        form_kwargs = super(AssociationGroupQuickLinksAddOrUpdateView, self).get_form_kwargs()
        form_kwargs["association_group"] = self.association_group
        return form_kwargs

    def get_success_message(self, form):
        if not form.cleaned_data["id"]:
            return f"{form.instance.name} has been added"
        else:
            return f"{form.instance.name} has been updated"

    def get_success_url(self):
        return reverse_lazy("committees:settings:group_quicklinks", kwargs={"group_id": self.association_group.id})


class AssociationGroupQuickLinksDeleteView(GroupSettingsMixin, PostOnlyFormViewMixin, FormView):
    form_class = DeleteGroupExternalUrlForm
    form_success_method_name = "delete"

    def get_form_kwargs(self):
        quicklink = self.association_group.shortcut_set.filter(id=self.kwargs.get("quicklink_id", None))
        if not quicklink.exists():
            raise Http404("This shortcut does not exist")

        form_kwargs = super(AssociationGroupQuickLinksDeleteView, self).get_form_kwargs()
        form_kwargs["instance"] = quicklink.first()
        return form_kwargs

    def get_success_url(self):
        return reverse_lazy("committees:settings:group_quicklinks", kwargs={"group_id": self.association_group.id})

    def get_success_message(self, form):
        return f"{form.instance.name} has been removed"


class AssociationGroupMembersView(GroupSettingsMixin, TemplateView):
    template_name = "committees/committee_pages/group_detail_members.html"
    form_class = AssociationGroupMembershipForm  # An empty form is displayed on the page

    def get_context_data(self, **kwargs):
        return super(AssociationGroupMembersView, self).get_context_data(
            form=self.form_class(association_group=self.association_group),
            member_links=self.association_group.associationgroupmembership_set.all(),
            **kwargs,
        )


class AssociationGroupMemberUpdateView(GroupSettingsMixin, PostOnlyFormViewMixin, FormView):
    form_class = AssociationGroupMembershipForm

    def get_form_kwargs(self):
        form_kwargs = super(AssociationGroupMemberUpdateView, self).get_form_kwargs()
        form_kwargs["association_group"] = self.association_group
        return form_kwargs

    def get_success_message(self, form):
        return f"{form.instance.member} has been updated"

    def get_success_url(self):
        return reverse_lazy("committees:settings:group_members", kwargs={"group_id": self.association_group.id})
