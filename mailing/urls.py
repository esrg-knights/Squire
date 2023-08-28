from django.urls import path, include

from . import views

urlpatterns = [
    path("layout/", views.EmailTemplateView.as_view(), name="layout"),
    path("layout/out/", views.EmailTemplateViewPopOut.as_view(), name="layout_out"),
    path("construct/", views.ConstructMailView.as_view(), name="construct")
]
