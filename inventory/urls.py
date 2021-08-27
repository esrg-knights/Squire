from django.urls import path, include, register_converter
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify

from inventory.views import *
from inventory.forms import OwnershipRemovalForm, OwnershipActivationForm
from inventory.models import Item


class CatalogueConverter:
    regex = '[\w.-]+'

    def to_python(self, value):
        content_types = Item.get_item_contenttypes()
        for item_type in content_types:
            if value == slugify(item_type.model_class().__name__):
                return item_type

        raise ValueError(f"There was no Item with name {value}")

    def to_url(self, value):
        if isinstance(value, ContentType):
            return slugify(value.model_class().__name__)
        elif isinstance(value, type) and issubclass(value, Item):
            return slugify(value.__name__)
        else:
            raise KeyError("Given value '{}' is not of a valid type".format(value))

register_converter(CatalogueConverter, 'cat_item')


####################################################


app_name = 'inventory'

urlpatterns = [
    path('my_items/', include([
        path('', MemberItemsOverview.as_view(), name='member_items'),
        path('<int:ownership_id>/', include([
            path('take_home/', MemberItemRemovalFormView.as_view(), name='member_take_home'),
            path('give_out/', MemberItemLoanFormView.as_view(), name='member_loan_out'),
            path('edit_note/', MemberOwnershipAlterView.as_view(), name='owner_link_edit'),
        ])),
    ])),

    path('catalogue/<cat_item:type_id>/', include([
        path('', TypeCatalogue.as_view(), name="catalogue"),
        path('add_new/', CreateItemView.as_view(), name='catalogue_add_new_item'),
        path('<int:item_id>/', include([
            path('update/', UpdateItemView.as_view(), name='catalogue_update_item'),
            path('delete/', DeleteItemView.as_view(), name='catalogue_delete_item'),
            path('links/', include([
                path('', ItemLinkMaintenanceView.as_view(), name='catalogue_item_links'),
                path('<int:link_id>/', include([
                    path('edit/', UpdateCatalogueLinkView.as_view(), name='catalogue_item_links'),
                    path('activate/', LinkActivationStateView.as_view(
                        form_class=OwnershipActivationForm), name='catalogue_item_link_activation'),
                    path('deactivate/', LinkActivationStateView.as_view(
                        form_class=OwnershipRemovalForm), name='catalogue_item_link_deactivation'),
                    path('delete/', LinkDeletionView.as_view(), name='catalogue_item_link_deletion')
                ])),
            ])),
            path('add_link/', include([
                path('group/', AddLinkCommitteeView.as_view(), name='catalogue_add_group_link'),
                path('member/', AddLinkMemberView.as_view(), name='catalogue_add_member_link')
            ])),

        ])),
    ])),

]
