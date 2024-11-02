from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.admin import GlobalPreferenceAdmin
from dynamic_preferences.models import GlobalPreferenceModel

from .models import MarkdownImage, PresetImage, Shortcut

from core.forms import MarkdownImageAdminForm
from utils.forms import RequestUserToFormModelAdminMixin


class DisableModificationsAdminMixin:
    """Mixin that disables modifications for an (Inline) admin"""

    # Disable creation
    def has_add_permission(self, request, obj=None):
        return False

    # Disable editing
    def has_change_permission(self, request, obj=None):
        return False

    # Disable deletion
    def has_delete_permission(self, request, obj=None):
        return False


class URLLinkInlineAdminMixin:
    """
    Mixin that adds a url to the admin change page of an Inline object.
    To use, add `"get_url"` to the Inline's `fields` and `readonly_fields`
    """

    def get_url(self, obj):
        content_type = ContentType.objects.get_for_model(obj)
        url = reverse(f"admin:{content_type.app_label}_{content_type.model}_change", args=[obj.id])
        return format_html("<a href='{0}'>View Details</a>", url)

    get_url.short_description = "Details"


###################################################


class SquireUserAdmin(UserAdmin):
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        ("member", admin.EmptyFieldListFilter),
        ("groups", admin.RelatedOnlyFieldListFilter),
        "date_joined",
        "last_login",
    )
    search_fields = ("username", "first_name", "email", "member__first_name", "member__last_name")
    search_help_text = "Search for username, account real name, member name"
    list_display = ("id", "username", "email", "first_name", "member", "is_staff", "is_superuser", "date_joined")
    list_display_links = ("id", "username")
    readonly_fields = ("member",)
    exclude = ("last_name",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "email", "member")}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


admin.site.unregister(User)
admin.site.register(User, SquireUserAdmin)


class SquireGroupAdmin(GroupAdmin):
    list_filter = (("associationgroup", admin.EmptyFieldListFilter),)
    search_fields = ("name", "associationgroup__shorthand")
    search_help_text = "Search for name, committee shorthand"
    list_display = ("id", "name", "has_assoc_group")
    list_display_links = ("id", "name")
    readonly_fields = ("associationgroup",)

    def has_assoc_group(self, obj):
        return bool(obj.associationgroup)

    has_assoc_group.short_description = "Is Committee"
    has_assoc_group.admin_order_field = "associationgroup"
    has_assoc_group.boolean = True


admin.site.unregister(Group)
admin.site.register(Group, SquireGroupAdmin)

###################################################
# Markdown Images


class PresetImageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "image", "selectable")
    list_filter = ["selectable"]
    list_display_links = ("id", "name")
    search_fields = ("name",)
    search_help_text = "Search for name"


admin.site.register(PresetImage, PresetImageAdmin)


class MarkdownImageInline(GenericTabularInline):
    model = MarkdownImage
    extra = 0
    max_num = 0  # Hides the "Add another Markdown image" button
    show_change_link = True
    readonly_fields = ["image", "upload_date", "uploader"]
    fields = ["image", "upload_date", "uploader"]
    ordering = ("-upload_date",)

    # Adding/Changing in this form doesn't actually work due to using a
    #   GenericForeignKey without a GenericRelation (for the backwards relation)
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class MarkdownImageAdmin(RequestUserToFormModelAdminMixin, admin.ModelAdmin):
    date_hierarchy = "upload_date"
    form = MarkdownImageAdminForm

    list_display = ("id", "content_type", "content_object", "uploader", "upload_date", "image")
    list_display_links = ("id", "content_type")
    list_filter = (
        ("uploader", admin.RelatedOnlyFieldListFilter),
        ("content_type", admin.RelatedOnlyFieldListFilter),
        ("object_id", admin.EmptyFieldListFilter),
    )
    search_fields = ("uploader__username",)
    search_help_text = "Search for uploader username"
    readonly_fields = ("upload_date", "content_object", "id", "uploader")
    ordering = ("-upload_date",)
    fieldsets = (
        (None, {"fields": ("id", "content_type", "object_id", "content_object", "image", "uploader", "upload_date")}),
    )

    # Make the content object a clickable link to that object's admin change form
    def content_object(self, obj):
        if obj.content_object is None:
            return "-"
        link = reverse(f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change", args=[obj.object_id])
        return mark_safe(f'<a href="{link}" target="_blank">{escape(str(obj.content_object))}</a>')

    # Limit content_type choices to valid models (according to the settings)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "content_type":
            kwargs["queryset"] = ContentType.objects.annotate(
                model_name=Concat("app_label", Value("."), "model", output_field=CharField())
            ).filter(model_name__in=settings.MARKDOWN_IMAGE_MODELS)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(MarkdownImage, MarkdownImageAdmin)


###################################################
# Global preferences admin panel.
#   We want to change the way some preference fields are rendered
class SquireGlobalPreferencesAdmin(GlobalPreferenceAdmin):
    list_display = ("id", "verbose_name", "description", "section_name")
    list_display_links = ("id", "verbose_name")

    fields = ("verbose_name", "description", "raw_value", "default_value", "section_name")
    readonly_fields = ("verbose_name", "description", "section_name", "default_value")
    search_fields = ["name", "verbose_name", "description", "section"]
    search_help_text = "Search for name, description, section"

    # Description of the permission
    def description(self, obj):
        return obj.preference.description or "-"

    # For MtM-relations, display text instead of primary keys
    def default_value(self, obj):
        if hasattr(obj.preference, "default_display"):
            return obj.preference.default_display
        if hasattr(obj.preference, "get_default_display"):
            return obj.preference.get_default_display()
        return obj.preference.default

    default_value.short_description = _("Default Value")


# Use our custom admin panel instead
admin.site.unregister(GlobalPreferenceModel)
admin.site.register(GlobalPreferenceModel, SquireGlobalPreferencesAdmin)
admin.site.register(Shortcut)
