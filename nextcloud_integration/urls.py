from django.urls import path, include

from . import views as views

urlpatterns = [
    path('browse/', views.FileBrowserView.as_view(), name=''),
    path('browse/<path:path>/', views.FileBrowserView.as_view(), name=''),
    path('form/', views.TestFormView.as_view(), name=''),
    path('form/<path:path>/', views.TestFormView.as_view(), name=''),
    path('folders/', include([
        path('', views.FolderView.as_view(), name='folder_view'),
        path('add', views.FolderCreateView.as_view(), name='add_folder'),
        path('<slug:folder_slug>/', include([
            path('', views.FolderContentView.as_view(), name='folder_view'),
            path('synch/', views.SynchFileToFolderView.as_view(), name='synch_file'),
            path('file/<slug:file_slug>', views.DownloadFileview.as_view(), name='file_dl'),
        ])),
    ])),

]
