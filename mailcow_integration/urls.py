from django.urls import path

from mailcow_integration.views import MailcowStatusView

app_name = 'mailcow_integration'

urlpatterns = [
    path('status', MailcowStatusView.as_view(), name='status'),
]
