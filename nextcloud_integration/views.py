from django.views.generic import ListView, FormView
from django.template.response import TemplateResponse

from nextcloud_integration.nextcloud_client import construct_client, OperationFailed
from nextcloud_integration.forms import FileMoveForm


class FileBrowserView(ListView):
    template_name = "nextcloud_integration/browser.html"
    context_object_name = 'nextcloud_resources'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(FileBrowserView, self).dispatch(request, *args, **kwargs)
        except OperationFailed as e:
            if e.actual_code == 404:
                return TemplateResponse(
                    request,
                    "nextcloud_integration/browser_not_exist.html",
                    {'folder': kwargs.get('path', '')}
                )


    def get_queryset(self):
        a = construct_client().ls(remote_path=self.kwargs.get('path', ''))
        print(a)
        return a

class TestFormView(FormView):
    form_class = FileMoveForm
    template_name = "nextcloud_integration/form.html"

    def get_form_kwargs(self):
        kwargs = super(TestFormView, self).get_form_kwargs()
        kwargs.update({
            'local_path': self.kwargs.get('path', '')
        })
        return kwargs

    def form_valid(self, form):
        form.execute()
        return super(TestFormView, self).form_valid(form)

    def get_success_url(self):
        return self.request.path
