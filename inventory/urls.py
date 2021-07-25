from django.urls import path, include

from inventory.views import *

namespace = 'inventory'

urlpatterns = [
    # Change Language helper view
    path('', BoardgameView.as_view(), name='home'),
    path('my_items/', include([
        path('', MemberItemsOverview.as_view(), name='member_items'),
        path('<int:ownership_id>/', include([
            path('take_ome/', MemberItemRemovalFormView.as_view(), name='member_take_home'),
            path('give_out/', MemberItemLoanFormView.as_view(), name='member_loan_out'),
        ])),
    ])),

]
