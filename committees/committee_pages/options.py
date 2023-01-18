from django.urls import path, include


from committees.models import AssociationGroup
from committees.committee_pages.views import *
from committees.options import SettingsOptionBase, settings


class InfoOptions(SettingsOptionBase):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.ORDER]
    name = 'home_info_text'
    title = "Home screen"
    template_name = "committees/committee_pages/setting_blocks/info.html"

    def build_url_pattern(self, config):
        return [path('update/', AssociationGroupUpdateView.as_view(config=config, settings_option=self), name='group_update')]


class MemberOptions(SettingsOptionBase):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.ORDER]
    name = 'member_basic'
    title = "Members"
    template_name = "committees/committee_pages/setting_blocks/members.html"

    def build_url_pattern(self, config):
        return [
            path('members/', AssociationGroupMembersView.as_view(config=config, settings_option=self), name='group_members'),
            path('members/edit/', AssociationGroupMemberUpdateView.as_view(config=config, settings_option=self), name='group_members_edit'),
        ]


class QuicklinkOptions(SettingsOptionBase):
    group_type_required = [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.ORDER]
    name = 'quicklinks'
    title = "External sources"
    template_name = "committees/committee_pages/setting_blocks/quicklinks.html"
    def build_url_pattern(self, config):
        return [
            path('quicklinks/', include([
                path('', AssociationGroupQuickLinksView.as_view(config=config, settings_option=self), name='group_quicklinks'),
                path('edit/', AssociationGroupQuickLinksAddOrUpdateView.as_view(config=config, settings_option=self), name='group_quicklinks_edit'),
                path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(config=config, settings_option=self), name='group_quicklink_delete'),
            ])),
        ]


settings.add_setting_option(MemberOptions)
settings.add_setting_option(QuicklinkOptions)
settings.add_setting_option(InfoOptions)
