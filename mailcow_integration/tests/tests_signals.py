from unittest.mock import Mock, patch
from django.contrib.auth.models import Group
from django.db.models.signals import pre_save
from django.test import TestCase
from dynamic_preferences.registries import global_preferences_registry
from committees.models import AssociationGroup, AssociationGroupMembership
from core.tests.util import suppress_infos
from mailcow_integration.api.exceptions import MailcowException

from mailcow_integration.signals import deregister_signals, global_preference_required_for_signal, register_signals
from mailcow_integration.squire_mailcow import SquireMailcowManager
from membership_file.models import Member, MemberYear, Membership


class MailcowSignalTestMixin:
    """Mixin that register/deregisters mailcow alias signals so that they don't interfere with other test cases"""

    def setUp(self) -> None:
        register_signals()
        self.global_preferences = global_preferences_registry.manager()
        self.global_preferences["mailcow__mailcow_signals_enabled"] = True

    @classmethod
    def tearDownClass(cls):
        # Deregister signals so they don't interfere with other tests
        deregister_signals()
        super().tearDownClass()


class GlobalPreferenceRequiredDecoratorTests(MailcowSignalTestMixin, TestCase):
    """Tests the global_preference_required_for_signal decorator"""

    def test_signal_activate_with_preference(self):
        """
        Tests if signals with @global_preference_required_for_signal only activate
        if the preference is set.
        """
        signal_mock = Mock(name="signal_fn")

        @global_preference_required_for_signal
        def foo(*args, **kwargs):
            signal_mock(*args, **kwargs)

        pre_save.connect(foo, sender=Group)

        # Signal should activate; preference is set
        Group.objects.create(name="Foo")
        signal_mock.assert_called_once()
        signal_mock.reset_mock()

        # Signal shouldn't activate; preference not set
        self.global_preferences["mailcow__mailcow_signals_enabled"] = False
        Group.objects.create(name="Bar")
        signal_mock.assert_not_called()


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.squire_mailcow.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class AliasSignalsTestsBase(MailcowSignalTestMixin, TestCase):
    """Base class for alias signal tests"""

    def reset(self, *args):
        """Resets all mock objects"""
        for mock in args:
            mock.reset_mock()


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class MemberAliasSignalsTests(AliasSignalsTestsBase):
    """Tests for alias signals for members"""

    def test_create_member(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when creating members"""
        # Newly created member is not active and is not part of a committee
        Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com", is_deregistered=True
        )
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # Newly created member is active, but not part of any committees
        Member.objects.create(first_name="Bar", last_name="", legal_name="Bar", email="bar@example.com")
        mock_m.assert_called_once()
        mock_c.assert_not_called()

    def test_update_member(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests updating member data"""
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com")
        group = AssociationGroup.objects.create(name="group", contact_email="comm@example.com")
        AssociationGroupMembership.objects.create(member=member, group=group)
        self.reset(mock_m, mock_c)

        # Email address didn't change; shouldn't update anything
        member.first_name = "Foo2"
        member.save()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # Email address changed
        member.email = "foobar@example.com"
        member.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["comm@example.com"])

    def test_delete_member(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests deleting member signals"""
        # active
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com")
        self.reset(mock_m, mock_c)
        member.delete()
        mock_m.assert_called_once()
        mock_c.assert_not_called()

        # inactive
        member = Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com", is_deregistered=True
        )
        self.reset(mock_m, mock_c)
        member.delete()
        mock_m.assert_not_called()
        mock_c.assert_not_called()


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class CommitteeAliasSignalsTests(AliasSignalsTestsBase):
    """Tests for alias signals for committees/orders"""

    def test_create_committee(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when creating committees"""
        # No email
        AssociationGroup.objects.create(name="group", contact_email=None, type=AssociationGroup.COMMITTEE)
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # Not a valid type
        AssociationGroup.objects.create(name="group2", contact_email="foo@example.com", type=AssociationGroup.BOARD)
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # Valid type and email
        AssociationGroup.objects.create(
            name="group3", contact_email="bar@example.com", type=AssociationGroup.COMMITTEE
        )
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["bar@example.com"])
        mock_gc.assert_called_once()
        mock_o.assert_not_called()

    def test_update_committee(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when updating committees"""
        group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.COMMITTEE
        )
        self.reset(mock_o, mock_c, mock_gc)

        # No changes
        group.save()
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # email -> no email
        group.contact_email = None
        group.save()
        mock_c.assert_not_called()
        mock_gc.assert_called_once()
        mock_o.assert_called_once()
        # Should still pass old email to Mailcow; it isn't yet aware of the change!
        self.assertListEqual(list(mock_o.call_args[0][0]), ["foo@example.com"])
        self.reset(mock_o, mock_c, mock_gc)

        # committee -> board (no email)
        group.type = AssociationGroup.BOARD
        group.save()
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # no email -> email (board)
        group.contact_email = "foo@example.com"
        group.save()
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # board -> committee (email)
        group.type = AssociationGroup.COMMITTEE
        group.save()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["foo@example.com"])
        mock_gc.assert_called_once()
        mock_o.assert_not_called()
        self.reset(mock_o, mock_c, mock_gc)

        # committee -> board (email)
        group.type = AssociationGroup.BOARD
        group.contact_email = "new@example.com"
        group.save()
        mock_c.assert_not_called()
        mock_gc.assert_called_once()
        mock_o.assert_called_once()
        # Should still pass old email to Mailcow; it isn't yet aware of the change!
        self.assertListEqual(list(mock_o.call_args[0][0]), ["foo@example.com"])

        # no email -> email (committee)
        group.type = AssociationGroup.COMMITTEE
        group.contact_email = None
        group.save()
        self.reset(mock_o, mock_c, mock_gc)
        group.contact_email = "foo@example.com"
        group.save()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["foo@example.com"])
        mock_gc.assert_called_once()
        mock_o.assert_not_called()
        self.reset(mock_o, mock_c, mock_gc)

    def test_delete_committee(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when deleting committees"""
        # Delete committee (email)
        group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.COMMITTEE
        )
        self.reset(mock_o, mock_c, mock_gc)
        group.delete()
        mock_c.assert_not_called()
        mock_gc.assert_called_once()
        mock_o.assert_called_once()
        # Should still pass old email to Mailcow; it isn't yet aware of the change!
        self.assertListEqual(list(mock_o.call_args[0][0]), ["foo@example.com"])

        # Delete committee (no email)
        group = AssociationGroup.objects.create(name="group", contact_email=None, type=AssociationGroup.COMMITTEE)
        self.reset(mock_o, mock_c, mock_gc)
        group.delete()
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()

        # Delete board
        group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.BOARD
        )
        self.reset(mock_o, mock_c, mock_gc)
        group.delete()
        mock_c.assert_not_called()
        mock_gc.assert_not_called()
        mock_o.assert_not_called()


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class CommitteeMembershipAliasSignalsTests(AliasSignalsTestsBase):
    """Tests for alias signals for adding members to committees/orders"""

    def test_create_committee_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when creating committee memberships"""
        c_group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.COMMITTEE
        )
        b_group = AssociationGroup.objects.create(
            name="group2", contact_email="bar@example.com", type=AssociationGroup.BOARD
        )
        i_group = AssociationGroup.objects.create(name="group3", contact_email=None, type=AssociationGroup.COMMITTEE)
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com")
        self.reset(mock_o, mock_c, mock_m)

        # Membership created for board
        AssociationGroupMembership.objects.create(member=member, group=b_group)
        mock_c.assert_not_called()
        mock_o.assert_not_called()

        # Membership created for committee with no email
        AssociationGroupMembership.objects.create(member=member, group=i_group)
        mock_c.assert_not_called()
        mock_o.assert_not_called()

        # Membership created with no member
        AssociationGroupMembership.objects.create(member=None, group=c_group)
        mock_c.assert_not_called()
        mock_o.assert_not_called()

        # Valid membership created
        AssociationGroupMembership.objects.create(member=member, group=c_group)
        mock_c.assert_called_once()
        self.assertIn("foo@example.com", list(mock_c.call_args[0][0]))
        mock_o.assert_not_called()

    def test_update_committee_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when updating committee memberships"""
        group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.COMMITTEE
        )
        group2 = AssociationGroup.objects.create(
            name="group2", contact_email="bar@example.com", type=AssociationGroup.COMMITTEE
        )
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="member@example.com")

        # no changes
        membership = AssociationGroupMembership.objects.create(member=member, group=group)
        self.reset(mock_c, mock_m)
        membership.save()
        mock_c.assert_not_called()

        # member -> nobody
        self.reset(mock_c)
        membership.member = None
        membership.save()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["foo@example.com"])

        # nobody -> member
        self.reset(mock_c)
        membership.member = member
        membership.save()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["foo@example.com"])

        # group changed
        self.reset(mock_c)
        membership.group = group2
        membership.save()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["bar@example.com", "foo@example.com"])

    def test_delete_committee_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when deleting committee memberships"""
        # No member
        group = AssociationGroup.objects.create(
            name="group", contact_email="foo@example.com", type=AssociationGroup.COMMITTEE
        )
        membership = AssociationGroupMembership.objects.create(member=None, group=group)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_c.assert_not_called()

        # Member
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="member@example.com")
        membership = AssociationGroupMembership.objects.create(member=member, group=group)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_c.assert_called_once()
        self.assertListEqual(list(mock_c.call_args[0][0]), ["foo@example.com"])


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class MemberYearAliasSignalsTests(AliasSignalsTestsBase):
    """Tests for alias signals for member years"""

    def test_create_memberyear(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when creating member years"""
        # New member year created (inactive)
        MemberYear.objects.create(name="year 1", is_active=False)
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # New member year created (active)
        MemberYear.objects.create(name="year 2", is_active=True)
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

        # New member year created (active), when there already was another active memberyear
        self.reset(mock_c, mock_m)
        MemberYear.objects.create(name="year 3", is_active=True)
        mock_m.assert_not_called()
        mock_c.assert_not_called()

    def test_update_memberyear(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when updating memberyears"""
        year = MemberYear.objects.create(name="year 1", is_active=True)

        # active -> inactive
        self.reset(mock_c, mock_m)
        year.is_active = False
        year.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

        # inactive -> active
        self.reset(mock_c, mock_m)
        year.is_active = True
        year.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

    def test_delete_memberyear(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when deleting memberyears"""
        # inactive
        year = MemberYear.objects.create(name="year 1", is_active=False)
        self.reset(mock_c, mock_m)
        year.delete()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # active
        year = MemberYear.objects.create(name="year 1", is_active=True)
        self.reset(mock_c, mock_m)
        year.delete()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases")
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases")
@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class MembershipAliasSignalsTests(AliasSignalsTestsBase):
    """Tests for alias signals for memberships (year-member link)"""

    def test_create_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when creating memberships"""
        year = MemberYear.objects.create(name="year 1", is_active=False)
        year_active = MemberYear.objects.create(name="year 1", is_active=True)
        member_active = Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="member@example.com"
        )
        member = Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="bar@example.com", is_deregistered=True
        )
        self.reset(mock_c, mock_m)

        # no member
        Membership.objects.create(member=None, year=year_active)
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # with member (inactive year)
        Membership.objects.create(member=member_active, year=year)
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # with member (active year, active member)
        Membership.objects.create(member=member_active, year=year_active)
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

        # with member (active year, inactive member)
        self.reset(mock_c, mock_m)
        Membership.objects.create(member=member, year=year_active)
        mock_m.assert_not_called()
        mock_c.assert_called_once_with()

    def test_update_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when updating memberships"""
        year_inactive = MemberYear.objects.create(name="year 1", is_active=False)
        year_active = MemberYear.objects.create(name="year 2", is_active=True)
        year_active_2 = MemberYear.objects.create(name="year 3", is_active=True)
        member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="member@example.com")
        membership = Membership.objects.create(member=member, year=year_active)

        # no change
        self.reset(mock_c, mock_m)
        membership.save()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # year changed (both active)
        self.reset(mock_c, mock_m)
        membership.year = year_active_2
        membership.save()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # year changed (active -> inactive)
        self.reset(mock_c, mock_m)
        membership.year = year_inactive
        membership.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

        # member changed (inactive year)
        self.reset(mock_c, mock_m)
        membership.member = None
        membership.save()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # year changed (inactive -> active)
        membership.member = member
        membership.save()
        self.reset(mock_c, mock_m)
        membership.year = year_active
        membership.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

        # member changed (active year)
        self.reset(mock_c, mock_m)
        membership.member = None
        membership.save()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()

    def test_delete_membership(self, _, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests signals when deleting memberships"""
        year_inactive = MemberYear.objects.create(name="year 1", is_active=False)
        year_active = MemberYear.objects.create(name="year 2", is_active=True)
        member_active = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="a@example.com")
        member_inactive = Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="b@example.com", is_deregistered=True
        )

        # inactive year
        membership = Membership.objects.create(member=member_active, year=year_inactive)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # no member
        membership = Membership.objects.create(member=None, year=year_active)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_m.assert_not_called()
        mock_c.assert_not_called()

        # inactive member
        membership = Membership.objects.create(member=member_inactive, year=year_active)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_m.assert_not_called()
        mock_c.assert_called_once_with()

        # active member
        membership = Membership.objects.create(member=member_active, year=year_active)
        self.reset(mock_c, mock_m)
        membership.delete()
        mock_m.assert_called_once()
        mock_c.assert_called_once_with()


@patch(
    "mailcow_integration.signals.get_mailcow_manager",
    return_value=SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key"),
)
class MiscAliasSignalTests(MailcowSignalTestMixin, TestCase):
    """Miscellaneous tests for Mailcow alias signals"""

    @patch(
        "mailcow_integration.squire_mailcow.SquireMailcowManager._set_alias_by_name", side_effect=MailcowException()
    )
    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.mailbox_map", return_value={})
    @suppress_infos(logger_name="mailcow_integration.squire_mailcow")
    def test_exception_handling(self, _, mock_a: Mock, mock_mailcow_manager: Mock):
        """Tests whether signals do not break when the API raises a MailcowException"""
        AssociationGroup.objects.create(
            name="group3", contact_email="bar@example.com", type=AssociationGroup.COMMITTEE
        )
        mock_a.assert_called_once()  # Sanity check
