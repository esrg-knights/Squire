from django.urls import path, re_path

from core.views import UrlRedirectView


urlpatterns = [
    re_path(r"^(?P<url_shortener>.*)/$", UrlRedirectView.as_view()),
]
