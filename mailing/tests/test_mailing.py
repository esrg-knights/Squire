from django.template import TemplateDoesNotExist
from django.test import TestCase

from . import MailTestingMixin

from mailing.mailing import Email, SimpleMessageEmail


class MailingTestCase(MailTestingMixin, TestCase):
    class CustomEmail(Email):
        template_name = "mailing/tests/test_custom_mail"

        def get_context_data(self):
            context = super().get_context_data()
            context["number"] = 50
            return context

        def get_recipient_context_data(self, recipient):
            context = super().get_recipient_context_data(recipient)
            context.update({"recipient_data": "BASED"})
            return context

        def _get_bcc_mail_addresses(self, recipient):
            return ["bcc@test.com"]

        def _get_from_mail_address(self):
            return "from_email@from.mail"

    def setUp(self):
        self.mail = self.CustomEmail(subject="Custom email")
        self.mail.send_to("send_to@test.com")
        self.send_mail = self.assertSendMail()

    def test_send_to(self):
        self.assertEqual(self.send_mail.to, ["send_to@test.com"])

    def test_send_from(self):
        self.assertEqual(self.send_mail.from_email, "from_email@from.mail")

    def test_send_bcc(self):
        self.assertEqual(self.send_mail.bcc, ["bcc@test.com"])

    def test_subject(self):
        self.assertEqual(self.send_mail.subject, self.mail.subject)

    def test_context_data(self):
        context_data = self.send_mail.context_data
        self.assertEqual(context_data["recipient"], "send_to@test.com")
        self.assertEqual(context_data["recipient_data"], "BASED")
        self.assertEqual(context_data["number"], 50)

    def test_require_subject(self):
        with self.assertRaises(KeyError):
            self.CustomEmail().send_to("to@test.com")
        self.CustomEmail(subject="Test subject").send_to("to@test.com")

    def test_txt_only_templates(self):
        Email(
            subject="Test subject",
            template_name="mailing/tests/test_txtonly_mail"
        ).send_to("to@test.com")

    def test_html_only_templates(self):
        with self.assertRaises(TemplateDoesNotExist):
            Email(
                subject="Test subject",
                template_name="mailing/tests/test_html_only_mail"
            ).send_to("to@test.com")


class SimpleMessageEmailTestCase(MailTestingMixin, TestCase):
    def test_simple_mail_sending(self):
        SimpleMessageEmail(message="Here is a message", subject="Mail subject").send_to(["test@test.test"])
        send_mail = self.assertSendMail()
        self.assertIn("Here is a message", self.get_html_template(send_mail))
        self.assertIn("Here is a message", send_mail.body)

    def test_send_as_bcc(self):
        mail = SimpleMessageEmail(message="Here is a message", subject="Mail subject")
        mail.send_as_bcc("", bcc_list=["bcc1@test.com", "bcc2@test.com"])
        send_mail = self.assertSendMail()
        self.assertIn("bcc2@test.com", send_mail.bcc)
