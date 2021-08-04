from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet

from inventory.models import *


class BaseGenericTweakedInlineFormSet(BaseGenericInlineFormSet):

    def is_valid(self):
        # Ownership items require an existing Item model. Formsets however set the link after cleaning
        # This is a bit annoying as it causes the instance to fail.
        # Thus we inject the instance before form validation into all new forms.
        for new_form in self.extra_forms:
            # Save the current instance in all objects
            new_form.instance.content_object = self.instance
        return super(BaseGenericTweakedInlineFormSet, self).is_valid()

class OwnershipInline(GenericTabularInline):
    model = Ownership
    extra = 0
    formset = BaseGenericTweakedInlineFormSet


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = [OwnershipInline,]

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'


class OwnershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'content_object')
    list_display_links = ('id', 'owner')
    # Note search_fields does not work on GenericRelation fields
    search_fields = ['group__name', 'member__first_name', 'member__last_name']

    autocomplete_fields = ['member', 'group']


admin.site.register(Ownership, OwnershipAdmin)
admin.site.register(BoardGame, BoardGameAdmin)
