from django.views.generic import View, TemplateView
from django.views.generic.edit import FormView
from django.http import Http404
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import get_template, TemplateDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .forms import MailForm, MailPreviewForm
from .inlining import MailInliner


class EmailTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "mailing/preview_mail.html"
    """
    A view to test mail templates with.
    The contentfactory class inside ensures that when an object does not reside in the context,
    it prints the query name instead
    """
    def get_context_data(self, *args, **kwargs):
        """ Create the context data """
        context = super(EmailTemplateView, self).get_context_data(*args, **kwargs)
        template_name = self.request.GET.get("template", "") + ".html"
        context["template_name"] = template_name

        form = MailPreviewForm(data=self.request.GET)
        if form.is_valid():
            html_template = mark_safe(form.render_mail_layout(self.request))
        else:
            html_template = "Template not found"
        context["html_template"] = html_template
        context["form"] = form

        return context


class EmailTemplateViewPopOut(EmailTemplateView):
    template_name = "mailing/preview_mail_raw.html"



class ConstructMailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """A view that allows users to send_to mails with the set mail adres"""
    template_name = "mailing/construct_mail.html"
    form_class = MailForm

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        form.send_email()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("mailing:construct")
