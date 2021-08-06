from django.urls import path, include

from inventory.views import *

app_name = 'inventory'

urlpatterns = [
    # Change Language helper view
    path('', BoardGameView.as_view(), name='home'),
    path('my_items/', include([
        path('', MemberItemsOverview.as_view(), name='member_items'),
        path('<int:ownership_id>/', include([
            path('take_home/', MemberItemRemovalFormView.as_view(), name='member_take_home'),
            path('give_out/', MemberItemLoanFormView.as_view(), name='member_loan_out'),
            path('edit_note/', MemberOwnershipAlterView.as_view(), name='owner_link_edit'),
        ])),
    ])),
    path('committee/<int:group_id>/', include([
        path('items/', GroupItemsOverview.as_view(), name='committee_items'),
        path('<int:ownership_id>/', include([
            path('edit_note/', GroupItemLinkUpdateView.as_view(), name='owner_link_edit'),
        ])),
    ])),

    path('catalogue/<int:type_id>/', include([
        path('', TypeCatalogue.as_view(), name="catalogue"),
        path('add_new/', CreateItemView.as_view(), name='catalogue_add_new_item'),
        path('<int:item_id>/', include([
            path('update/', UpdateItemView.as_view(), name='catalogue_update_item'),
            path('delete/', DeleteItemView.as_view(), name='catalogue_delete_item'),
            path('add_link/', include([
                path('group/', AddLinkCommitteeView.as_view(), name='catalogue_add_group_link'),
                path('member/', AddLinkMemberView.as_view(), name='catalogue_add_member_link')
            ])),

        ])),
    ])),

]
