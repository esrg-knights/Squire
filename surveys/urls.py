from django.urls import path, include, register_converter
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify

from surveys.views import *


app_name = 'surveys'

urlpatterns = [
    path('', SurveyOverview.as_view(), name='overview'),
    path('<int:survey_id>/', include([
        path('', SurveyFormView.as_view(), name='fill_in'),
    ])),

]
