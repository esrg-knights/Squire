from django.urls import path, include

from . import views as views

urlpatterns = [
    path('browse/', views.FileBrowserView.as_view(), name=''),
    path('browse/<path:path>/', views.FileBrowserView.as_view(), name=''),
    path('folders/', include([
        path('', views.FolderView.as_view(), name='folder_view'),
        path('add', views.FolderCreateView.as_view(), name='add_folder'),
        path('<slug:folder_slug>/', include([
            path('', views.FolderContentView.as_view(), name='folder_view'),
            path('edit/', views.FolderCreateView.as_view(), name='folder_edit'),
            path('synch/', views.SynchFileToFolderView.as_view(), name='synch_file'),
            path('file/<slug:file_slug>', views.DownloadFileview.as_view(), name='file_dl'),
        ])),
    ])),
    path('downloads/', views.SiteDownloadView.as_view(), name='site_downloads')

]
