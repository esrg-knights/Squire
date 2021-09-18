from django.conf import settings
from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.admin import GlobalPreferenceAdmin
from dynamic_preferences.models import GlobalPreferenceModel

from .models import MarkdownImage, PresetImage

from core.forms import MarkdownImageAdminForm
from utils.forms import RequestUserToFormModelAdminMixin

###################################################
# Backport of Django 3.1
class EmptyFieldListFilter(admin.FieldListFilter): # pragma: no cover
    def __init__(self, field, request, params, model, model_admin, field_path):
        # https://code.djangoproject.com/ticket/31952
        # This bug is fixed in future versions of Django, though this is done in
        #   another place than this filter. We'll make our own "fix" here instead
        #   until we upgrade
        if not getattr(field, 'empty_strings_allowed', False) and not field.null:
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
        # Same as above
        if getattr(self.field, 'empty_strings_allowed', False):
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


class SquireUserAdmin(UserAdmin):
    list_filter = (
        'is_staff', 'is_superuser', 'is_active',
        ('member', EmptyFieldListFilter),
        ('groups', admin.RelatedOnlyFieldListFilter),
        'date_joined', 'last_login'
    )
    search_fields = ('username', 'first_name', 'email', 'member__first_name', 'member__last_name')
    list_display = ('id', 'username', 'email', 'first_name', 'member', 'is_staff', 'is_superuser', 'date_joined')
    list_display_links = ('id', 'username')
    readonly_fields = ('member',)
    exclude=('last_name',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'email', 'member')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

admin.site.unregister(User)
admin.site.register(User, SquireUserAdmin)

class SquireGroupAdmin(GroupAdmin):
    list_filter = (
        ('associationgroup', EmptyFieldListFilter),
    )
    search_fields = ('name', 'associationgroup__shorthand')
    list_display = ('id', 'name', 'has_assoc_group')
    list_display_links = ('id', 'name')
    readonly_fields = ('associationgroup',)

    def has_assoc_group(self, obj):
        return bool(obj.associationgroup)
    has_assoc_group.short_description = "Is Committee"
    has_assoc_group.admin_order_field = 'associationgroup'
    has_assoc_group.boolean = True

admin.site.unregister(Group)
admin.site.register(Group, SquireGroupAdmin)

###################################################
# Markdown Images

class PresetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'selectable')
    list_filter = ['selectable']
    list_display_links = ('id', 'name')
    search_fields = ('name',)

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

class MarkdownImageAdmin(RequestUserToFormModelAdminMixin, admin.ModelAdmin):
    date_hierarchy = 'upload_date'
    form = MarkdownImageAdminForm

    list_display = ('id', 'content_type', 'content_object', 'uploader', 'upload_date', 'image')
    list_display_links = ('id', 'content_type')
    list_filter = (
        ('uploader',        admin.RelatedOnlyFieldListFilter),
        ('content_type',    admin.RelatedOnlyFieldListFilter),
        ('object_id',       EmptyFieldListFilter),
    )
    search_fields = ('uploader__username',)
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

admin.site.register(MarkdownImage, MarkdownImageAdmin)

###################################################
# Global preferences admin panel.
#   We want to change the way some preference fields are rendered
class SquireGlobalPreferencesAdmin(GlobalPreferenceAdmin):
    list_display = ('id', 'verbose_name', 'description', 'section_name')
    list_display_links = ('id', 'verbose_name')

    fields = ('verbose_name', 'description', 'raw_value', 'default_value', 'section_name')
    readonly_fields = ('verbose_name', 'description', 'section_name', 'default_value')
    search_fields = ['name', 'verbose_name', 'description', 'section']

    # Description of the permission
    def description(self, obj):
        return obj.preference.description or '-'

    # For MtM-relations, display text instead of primary keys
    def default_value(self, obj):
        if hasattr(obj.preference, 'default_display'):
            return obj.preference.default_display
        if hasattr(obj.preference, 'get_default_display'):
            return obj.preference.get_default_display()
        return obj.preference.default
    default_value.short_description = _("Default Value")

# Use our custom admin panel instead
admin.site.unregister(GlobalPreferenceModel)
admin.site.register(GlobalPreferenceModel, SquireGlobalPreferencesAdmin)
