from django.urls import path
from . import views

urlpatterns = [
    path('', views.activity_collection, name='activity_collection'),
]