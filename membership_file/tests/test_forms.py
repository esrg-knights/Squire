from django.test import TestCase

from utils.testing.form_test_util import FormValidityMixin
from membership_file.forms import ContinueMembershipForm
from membership_file.models import Member, MemberYear, Membership


class ContinueMembershipFormTest(FormValidityMixin, TestCase):
    fixtures = ["test_users", "test_members"]
    form_class = ContinueMembershipForm

    def test_form_validity(self):
        # This already exists
        self.assertFormHasError(
            {},
            "already_member",
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=1),
        )
        self.assertFormValid(
            {},
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=3),
        )

    def test_saving(self):
        form = self.assertFormValid(
            {},
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=3),
        )
        form.save()
        self.assertTrue(Membership.objects.filter(member_id=1, year_id=3).exists())

    def test_form_kwarg_requirements(self):
        """Test that the required keyword arguments are checked (i.e. year and member may not be none)"""
        with self.assertRaises(AssertionError):
            self.build_form(
                {},
                member=Member.objects.get(id=1),
                year=MemberYear.objects.filter(id=999).first(),
            )
        with self.assertRaises(AssertionError):
            self.build_form(
                {},
                member=Member.objects.filter(id=999).first(),
                year=MemberYear.objects.get(id=1),
            )
