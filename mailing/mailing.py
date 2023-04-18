import re
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import get_template, TemplateDoesNotExist
from functools import cached_property


class Mail:
    """
    Renders and sends emails in a predefined template. It's basically the email alternative to the View class
    :param template_name: The path and name of the template (without extention)
    """
    template_name:str = None
    subject:str = None

    @cached_property
    def txt_template(self):
        try:
            return self._get_mail_templates("txt")
        except TemplateDoesNotExist as e:
            raise TemplateDoesNotExist(
                f"Could not find a txt template for {self.template_name}.txt. Make sure the path is correctly linked "
                f"with a txt file as any e-mail MUST contain a txt body. HTML template is optional."
            ) from e

    @cached_property
    def html_template(self):
        try:
            return self._get_mail_templates("html")
        except TemplateDoesNotExist:
            return None

    def __init__(self, template_name: str=None, subject: str=None):
        self.template_name = template_name or self.template_name
        self.subject = subject or self.subject

    def _get_mail_templates(self, extension:str ):
        """ Gets the mail template with the given extention """
        return get_template(f"{self.template_name}.{extension}", using='EmailTemplates')

    def get_mail_subject(self):
        """ Returns the subject of the mail """
        if self.subject:
            return self.subject
        else:
            raise KeyError(f"No mail_subject is defined for {self.__class__.__name__}. Make sure to set the "
                           f"mail_subject attribute or overwrite the 'get_mail_subject' method")

    def get_connection(self):
        return get_connection()

    def get_context_data(self):
        return {}

    def get_recipient_context_data(self, recipient):
        return {
            "recipient": recipient,
        }

    def _get_to_mail_addresses(self, recipient:str):
        """ Returns the e-mail address from the recipient  instance. Can be overwritten to use User other sources """
        if isinstance(recipient, str):
            regexp = re.compile(r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', re.IGNORECASE)
            email = regexp.findall(recipient)
            if email:
                return email
            else:
                raise AttributeError(f"{recipient} is not a valid e-mail address")
        else:
            raise AttributeError(f"Expected email string as recipient not {recipient.__repr__()}")

    def _get_bcc_mail_addresses(self, recipient):
        """
        Returns a list of email adresses to include in the bcc
        :param recipient: The recipient of the mail
        :return: A list of email strings
        """
        return []

    def _get_from_mail_address(self):
        """ Returns the from email address """
        # None defaults the from email to the settings DEFAULT_FROM_EMAIL
        return None

    def send_to(self, recipients, fail_silently=False):
        """
        Send emails to the recipients
        :param recipients: Single instance or iteration of recipients. Initially expected email string
        :param fail_silently: A boolean. When it’s False, send_mail() will raise an smtplib.SMTPException if an error occurs.
        :return:
        """
        context = self.get_context_data()

        # Open the connection
        connection = self.get_connection()
        connection.open()
        for recipient in recipients:
            # Make sure the context is not overwritten  and update it with recipient info
            local_context = context.copy()
            local_context.update(self.get_recipient_context_data(recipient))
            self._send_single_email_to(recipient, local_context, connection=connection, fail_silently=fail_silently)
        connection.close()

    def _send_single_email_to(self, recipient, context_data:dict, connection=None, fail_silently=False):
        """
        Constructs a single email and sends it
        :param recipient: The recipient
        :param context: The context for template rendering
        :param connection: The connection for mailing
        :return:
        """
        # Set up the Email template with the txt_template
        mail_obj = EmailMultiAlternatives(
            subject=self.get_mail_subject(),
            from_email=self._get_from_mail_address(),
            to=self._get_to_mail_addresses(recipient),
            body=self.txt_template.render(context_data),
            connection=connection,
            bcc=self._get_bcc_mail_addresses(recipient)
        )

        # Set up the html content in the mail
        if self.html_template is not None:
            content_html = self.html_template.render(context_data)
            mail_obj.attach_alternative(content_html, "text/html")

        # Send the mail
        mail_obj.send(fail_silently=fail_silently)


class SimpleMessageMail(Mail):
    template_name = "mailing/simple_message"

    def __init__(self, message, **kwargs):
        self.message = message
        super(SimpleMessageMail, self).__init__(**kwargs)

    def get_context_data(self):
        context = super(SimpleMessageMail, self).get_context_data()
        context['message'] = self.message
        return context
