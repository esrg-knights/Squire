from django.urls import path, include

from . import views as views

urlpatterns = [
    path('browse/', views.FileBrowserView.as_view(), name=''),
    path('browse/<path:path>/', views.FileBrowserView.as_view(), name=''),
    path('form/', views.TestFormView.as_view(), name=''),
    path('form/<path:path>/', views.TestFormView.as_view(), name=''),
]
