from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Value, Q
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.html import escape, mark_safe

from .models import PresetImage, MarkdownImage

###################################################
from django.utils.translation import gettext_lazy as _

# Backport of Django 3.1
class EmptyFieldListFilter(admin.FieldListFilter): # pragma: no cover
    def __init__(self, field, request, params, model, model_admin, field_path):
        if not field.empty_strings_allowed and not field.null:
            raise ImproperlyConfigured(
                "The list filter '%s' cannot be used with field '%s' which "
                "doesn't allow empty strings and nulls." % (
                    self.__class__.__name__,
                    field.name,
                )
            )
        self.lookup_kwarg = '%s__isempty' % field_path
        self.lookup_val = params.get(self.lookup_kwarg)
        super().__init__(field, request, params, model, model_admin, field_path)

    def queryset(self, request, queryset):
        if self.lookup_kwarg not in self.used_parameters:
            return queryset
        if self.lookup_val not in ('0', '1'):
            raise IncorrectLookupParameters

        lookup_condition = Q()
        if self.field.empty_strings_allowed:
            lookup_condition |= Q(**{self.field_path: ''})
        if self.field.null:
            lookup_condition |= Q(**{'%s__isnull' % self.field_path: True})
        if self.lookup_val == '1':
            return queryset.filter(lookup_condition)
        return queryset.exclude(lookup_condition)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def choices(self, changelist):
        for lookup, title in (
            (None, _('All')),
            ('1', _('Empty')),
            ('0', _('Not empty')),
        ):
            yield {
                'selected': self.lookup_val == lookup,
                'query_string': changelist.get_query_string({self.lookup_kwarg: lookup}),
                'display': title,
            }

###################################################

class PresetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'selectable')
    list_filter = ['selectable']
    list_display_links = ('id', 'name')

admin.site.register(PresetImage, PresetImageAdmin)


class MarkdownImageInline(GenericTabularInline):
    model = MarkdownImage
    extra = 0
    show_change_link = True
    readonly_fields = ['image', 'upload_date', 'uploader']
    fields = ['image', 'upload_date', 'uploader']
    ordering = ("-upload_date",)

    # Adding/Changing in this form doesn't actually work due to using a
    #   GenericForeignKey without a GenericRelation (for the backwards relation)
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class MarkdownImageAdmin(admin.ModelAdmin):
    date_hierarchy = 'upload_date'

    list_display = ('id', 'content_type', 'content_object', 'uploader', 'upload_date', 'image')
    list_display_links = ('id', 'content_type')
    list_filter = (
        ('uploader',        admin.RelatedOnlyFieldListFilter),
        ('content_type',    admin.RelatedOnlyFieldListFilter),
        ('object_id',       EmptyFieldListFilter),
    )
    readonly_fields = ('upload_date', 'content_object', 'id', 'uploader')
    ordering = ("-upload_date",)
    fieldsets = (
        (None, {'fields': ('id', 'content_type', 'object_id', 'content_object', 'image', 'uploader', 'upload_date')}),
    )

    # Make the content object a clickable link to that object's admin change form
    def content_object(self, obj):
        if obj.content_object is None:
            return '-'
        link = reverse(f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change", args=[obj.object_id])
        return mark_safe(f'<a href="{link}" target="_blank">{escape(str(obj.content_object))}</a>')

    # Limit content_type choices to valid models (according to the settings)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "content_type":
            kwargs["queryset"] = ContentType.objects \
                .annotate(model_name=Concat('app_label', Value('.'), 'model', output_field=CharField())) \
                .filter(model_name__in=settings.MARKDOWN_IMAGE_MODELS)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Set the image's uploader (the user that last edited the instance)
    def save_model(self, request, obj, form, change):
        obj.uploader = request.user
        super().save_model(request, obj, form, change)

admin.site.register(MarkdownImage, MarkdownImageAdmin)
