from django.urls import path, include

from roleplaying.views import *

namespace = 'roleplaying'

urlpatterns = [
    # Change Language helper view
    path('systems/', include([
        path('', RoleplaySystemView.as_view(), name='home'),
        path('<int:system_id>/', include([
            path('details/', SystemDetailView.as_view(), name='system_details'),
            path('edit/', SystemUpdateView.as_view(), name='system_edit'),
        ])),
    ])),

    path('item/<int:item_id>/download/', DownloadDigitalItemView.as_view(), name='download_roleplay_item'),

]
