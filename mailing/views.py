from django.views.generic import View
from django.views.generic.edit import FormView
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.template.loader import get_template, TemplateDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .forms import MailForm


class EmailTemplateView(LoginRequiredMixin, View):
    """
    A view to test mail templates with.
    The contentfactory class inside ensures that when an object does not reside in the context,
    it prints the query name instead
    """

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
                if hasattr(item, '__getattr__') or hasattr(item, '__getitem__'):
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

    def get_context_data(self, request):
        """ Create the context data """
        context = self.ContentFactory(dictionary=request.GET.dict())
        context['request'] = request
        context['user'] = request.user
        return context

    def get(self, request):
        template_location = request.GET.get("template", "") + ".html"
        try:
            context = self.get_context_data(request)
            return render(None, template_location, context, using="EmailTemplates")
        except TemplateDoesNotExist:
            raise Http404(f"Given template name not found: {template_location}")


class ConstructMailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """ A view that allows users to send_to mails with the set mail adres """
    template_name = "mailing/construct_mail.html"
    form_class = MailForm

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        form.send_email()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('mailing:construct')
