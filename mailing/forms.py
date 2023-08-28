from django import forms
from django.forms import ValidationError
from django.template.loader import get_template, TemplateDoesNotExist
from django.urls import reverse

from .mailing import SimpleMessageEmail
from .inlining import MailInliner


class MailForm(forms.Form):
    """A simple form to construct and send_to e-mails"""

    to = forms.EmailField()
    subject = forms.CharField(max_length=128)
    text = forms.CharField(widget=forms.Textarea)

    def send_email(self):
        """Sends the constructed e-mail"""
        if self.is_valid():
            SimpleMessageEmail(
                message=self.cleaned_data['text'],
                subject=self.cleaned_data['subject']
            ).send_to([self.cleaned_data['to']])
        else:
            raise forms.ValidationError("Form not valid yet")


class MailPreviewForm(forms.Form):
    """ A form that aids in displaying previews of an email. Useful when making new layouts in dev mode """
    template_name = forms.CharField(max_length=64)

    class ContentFactory(dict):
        """
        A dictionary that either returns the content, or a new dictionary with the name of the searched content
        Used to replace unfound content in the template with the original name
        """

        def __init__(self, name="", dictionary=None):
            self._dict = dictionary
            self._name = name

        def __getattr__(self, key):
            return self[key]

        def __getitem__(self, key):
            # Create the name of the new object if needed
            name = "{name}.{key}".format(name=self._name, key=key)

            # If the wrappwer is empty, return a new wrapper
            if self._dict is None:
                return type(self)(name=name)

            # There is an object, so search the object
            try:
                # Dictionary lookup
                item = self._dict[key]
            except (AttributeError, KeyError, TypeError):
                # Dictionary lookup failed. Try attribute lookup
                try:
                    item = getattr(self._dict, key)
                except (TypeError, AttributeError):
                    item = None

            if callable(item):
                # Check if item is callable
                try:  # method call (assuming no args required)
                    item = item()
                except TypeError:
                    item = None

            if item is None:
                # If key is not in dictionary, create a new ContentFactory to act as a query shell
                return type(self)(name=name)
            else:
                if hasattr(item, "__getattr__") or hasattr(item, "__getitem__"):
                    return type(self)(name=name, dictionary=item)
                return item

        def __contains__(self, item):
            # All objects exist, either in the dictionary, or a new one is created
            return True

        def __str__(self):
            # Check if the wrapper encompasses an object, if so, print the object, otherwise print itself
            if self._dict is None:
                return "- {} -".format(self._name)
            else:
                return "> {} <".format(self._dict.__str__())

        def __setitem__(self, key, value):
            # create a dict if it does not exist
            if self._dict is None:
                self._dict = {}
            # Add the entry in the dict
            self._dict[key] = value

    def clean_template_name(self):
        template_name = self.cleaned_data["template_name"]
        if not template_name.endswith(".html"):
            template_name = template_name + ".html"
        try:
            get_template(template_name, using="EmailTemplates")
            return template_name
        except TemplateDoesNotExist:
            raise ValidationError("Template name does not exist", code="does_not_exist")

    def get_mail_context_data(self, request):
        context = self.ContentFactory(dictionary=request.GET.dict())
        context["request"] = request
        context["user"] = request.user
        return context

    def render_mail_layout(self, request):
        try:
            template = get_template(self.cleaned_data["template_name"], using="EmailTemplates")
        except TemplateDoesNotExist:
            return "Template does not exist"
        else:
            context = self.get_mail_context_data(request)
            layout = template.render(context)
            layout = MailInliner.inline(layout)
            return layout

    def get_absolute_url(self):
        return reverse("mailing:layout_out") + "?template_name="+self.cleaned_data["template_name"]


