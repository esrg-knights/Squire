from django.test import TestCase
from django.forms import ValidationError

from utils.testing import FormValidityMixin

from mailing.forms import MailForm
from mailing.mailing import SimpleMessageEmail
from . import MailTestingMixin


class MailFormTestCase(FormValidityMixin, MailTestingMixin, TestCase):
    form_class = MailForm

    def test_send_mail(self):
        """Tests that normal form data is valid"""
        form = self.assertFormValid({
                "to": "test@test.com",
                "subject": "Subject",
                "text": "This is a message",
        })
        form.send_email()
        self.assertSendMail(subject="Subject", email_class=SimpleMessageEmail)

    def test_send_without_validation(self):
        form = self.build_form({
            "to": "",
            "subject": "Subject",
            "text": "This is a message",
        })
        with self.assertRaises(ValidationError):
            form.send_email()
