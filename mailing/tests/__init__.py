from django.core import mail
from django.test import TestCase
from django.test.utils import modify_settings, override_settings
from typing import Union


__all__ = ["MailTestingMixin"]


class MailTestingMixin(TestCase):
    def assertSendMail(self, subject=None, email_class=None, to=None) -> mail.EmailMessage:
        """
        Asserts that an email has been send
        :param subject: The subject of the email
        :param email_class: The Email class
        :param to: the email address of the receiver
        :return:
        """
        if to:
            if isinstance(to, str):
                to = [to]
            if not isinstance(to, (list, tuple)):
                raise KeyError(
                    "To attribute fo assertSendMail should be a string, or list or tuple of string instances"
                )

        for email in mail.outbox:
            if subject and email.subject != subject:
                continue
            # email_class is given to the email by the Email class, but we can not assume a mail is send by such
            # a class. So check if the property is availlable first
            if email_class and hasattr(email, "email_class"):
                if email.email_class != email_class:
                    continue
            if to and not set(to).issubset(email.to):
                continue
            return email
        msg = "No email has been found with the given for the given criteria: "
        if not subject and not email_class and not to:
            msg += "-,"
        else:
            if subject:
                msg += f"subject='{subject}', "
            if email_class:
                msg += f"email_class='{email_class.__name__}', "
            if to:
                msg += f"to='{to}', "
        if len(mail.outbox) > 0:
            msg += f" a total of {len(mail.outbox)} emails were send."
        else:
            msg += " a total of 0 emails have been send. Make sure you have triggered the send_to() method."
        raise AssertionError(msg)

    @staticmethod
    def get_html_template(mail_message: mail.EmailMultiAlternatives) -> Union[str, None]:
        """Returns the html template associated with the e-mail"""
        for content, minetype in mail_message.alternatives:
            if minetype == "text/html":
                return content
        return None


class CustomTestSite:
    """
        A class that shares the primary interface of Site (i.e., it has ``domain``
        and ``name`` attributes) but it returns simple test values
    """
    domain = "test.com"
    name = "Test site"
