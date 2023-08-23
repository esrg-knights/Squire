from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from committees.admin.forms import AssociationGroupsTabAccessForm
from committees.admin.models import AssociationGroupPanelControl
from committees.admin.options import GroupPanelAccessAdmin


class GroupPanelAccessAdminTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members", "committees/associationgroups"]
    base_user_id = 1

    def setUp(self):
        self.model_admin = GroupPanelAccessAdmin(model=AssociationGroupPanelControl, admin_site=admin)
        super(GroupPanelAccessAdminTestCase, self).setUp()

    def test_static_attributes(self):
        self.assertEqual(
            GroupPanelAccessAdmin.change_form_template,
            "committees/admin/change_group_tab_access.html",
        )
        self.assertEqual(GroupPanelAccessAdmin.list_display, ("id", "name"))
        self.assertEqual(GroupPanelAccessAdmin.list_display_links, ("id", "name"))

    def test_delete_permission(self):
        self.client.request()
        self.assertEqual(self.model_admin.has_delete_permission(self.client.get("").request), False)

    def test_add_permission(self):
        self.assertEqual(self.model_admin.has_delete_permission(self.client.get("").request), False)

    def test_get_form(self):
        self.assertEqual(self.model_admin.get_form(None), AssociationGroupsTabAccessForm)

    def test_succesful_list(self):
        self.assertValidGetResponse(url=reverse("admin:committees_associationgrouppanelcontrol_changelist"))

    def test_succesful_change_get(self):
        self.assertValidGetResponse(
            url=reverse("admin:committees_associationgrouppanelcontrol_change", kwargs={"object_id": 1})
        )

    def test_succesful_change_post(self):
        self.assertValidPostResponse(
            data={"_continue": True},
            url=reverse("admin:committees_associationgrouppanelcontrol_change", kwargs={"object_id": 1}),
            redirect_url=reverse("admin:committees_associationgrouppanelcontrol_change", kwargs={"object_id": 1}),
        )
