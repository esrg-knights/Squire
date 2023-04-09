from django.urls import path, include

from . import views as views

# fmt: off
urlpatterns = [
    path('browse/', views.FileBrowserView.as_view(), name='browse_nextcloud'),
    path('browse/<path:path>/', views.FileBrowserView.as_view(), name='browse_nextcloud'),
    path('folders/', include([
        path('add', views.FolderCreateView.as_view(), name='add_folder'),
        path('<slug:folder_slug>/', include([
            path('edit/', views.FolderEditView.as_view(), name='folder_edit'),
            path('sync/', views.SyncFileToFolderView.as_view(), name='sync_file'),
            path('file/<slug:file_slug>', views.DownloadFileview.as_view(), name='file_dl'),
        ])),
    ])),
    path('downloads/', views.SiteDownloadView.as_view(), name='site_downloads')

]
