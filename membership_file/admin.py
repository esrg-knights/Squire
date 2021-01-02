from django.contrib import admin
from django.utils.html import format_html

from .forms import MemberRoomForm
from .models import Member, MemberLog, MemberLogField, Room


class HideRelatedNameAdmin(admin.ModelAdmin):
    class Media:
        # Hacky solution to hide the "X was updated: <Y> -> <Z>" text
        # We don't need to edit this information anyways, so it's safe to hide
        # https://stackoverflow.com/a/5556813
        css = {
            'all': ('css/hide_related_model_name.css',),
        }

class DisableModifications():
    # Disable creation
    def has_add_permission(self, request):
        return False
    
    # Disable editing
    def has_change_permission(self, request, obj=None):
        return False

    # Disable deletion
    def has_delete_permission(self, request, obj=None):
        return False

class RoomInline(admin.TabularInline):
    model = Room.members_with_access.through
    extra = 0


class MemberLogReadOnlyInline(DisableModifications, admin.TabularInline):
    model = MemberLog
    extra = 0
    readonly_fields = ['date', 'get_url']
    fields = ['log_type', 'user', 'date', 'get_url']
    ordering = ("-date",)

    # Whether the object can be deleted inline
    can_delete = False

    def get_url(self, obj):
        return format_html("<a href='/admin/membership_file/memberlog/{0}/change/'>View Details</a>", obj.id)
    get_url.short_description = 'Details'

# Ensures that the last_updated_by field is also updated properly from the Django admin panel
class MemberWithLog(HideRelatedNameAdmin):
    form = MemberRoomForm

    list_display = ('id', 'user', 'first_name', 'tussenvoegsel', 'last_name', 'educational_institution', 'is_deregistered', 'marked_for_deletion')
    list_filter = ['educational_institution', 'marked_for_deletion', 'is_deregistered', 'has_paid_membership_fee', 'is_honorary_member']
    list_display_links = ('id', 'user', 'first_name')
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'external_card_number']

    # Display a search box instead of a dropdown menu
    autocomplete_fields = ['user']

    fieldsets = [
        (None, {'fields':
            ['user', ('first_name', 'tussenvoegsel', 'last_name'),
            'marked_for_deletion', 'preferred_pronoun',
            ('last_updated_date', 'last_updated_by'),]}),
        ('Membership Status', {'fields': 
            ['is_deregistered', 'has_paid_membership_fee', 'is_honorary_member', 'member_since']}),
        ('Contact Details', {'fields': 
            ['email', 'phone_number',
            ('street', 'house_number', 'house_number_addition'), ('postal_code', 'city'), 'country']}),
        ('Room Access', {'fields':
            ['key_id', 'tue_card_number', 
            ('external_card_number', 'external_card_digits', 'external_card_cluster'),
            'external_card_deposit', 'accessible_rooms', 'normally_accessible_rooms']}),
        ('Legal Information', {'fields':
            ['educational_institution', 'student_number',
            'date_of_birth', 'legal_name']}),
        ('Notes', {'fields':
            ['notes']}),
    ]

    inlines = [MemberLogReadOnlyInline]

    # Show the date and user that last updated the member
    # Override the admin panel's save method to automatically include the user that updated the member
    def save_model(self, request, obj, form, change):
        obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)

    # Disable field editing if the member was marked for deletion (except the marked_for_deletion field)
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ['last_updated_by', 'last_updated_date']
        if obj is None or not obj.marked_for_deletion:
            return readonly_fields
        readonly_fields = list(set(
            readonly_fields +
            [field.name for field in self.opts.local_fields] +
            [field.name for field in self.opts.local_many_to_many]
        ))
        readonly_fields.remove('marked_for_deletion')
        return readonly_fields

    # Disable deletion if the member was not marked for deletion
    # Disable deletion for the user that marked the member for deletion
    def has_delete_permission(self, request, obj=None):
        # User is normally allowed to delete these objects
        if obj is None:
            return True
        
        # If the member was not marked for deletion, disable deletion
        if not obj.marked_for_deletion:
            return False
        # If the member was marked for deletion by the requesting user, disable deletion
        elif (obj.last_updated_by is None) or (obj.last_updated_by.id == request.user.id):
            return False

        # The member was marked for deletion, and is being deleted by another user; enable deletion
        return True

# Prevents MemberLogField creation, edting, or deletion in the Django Admin Panel
class MemberLogFieldReadOnlyInline(DisableModifications, admin.TabularInline):
    model = MemberLogField
    extra = 0

    # Whether the object can be deleted inline
    can_delete = False

# Prevents MemberLog creation, edting, or deletion in the Django Admin Panel
class MemberLogReadOnly(DisableModifications, HideRelatedNameAdmin):
    # Show the date at which the information was updated as well
    readonly_fields = ['date']
    list_display = ('id', 'log_type', 'user', 'member', 'date')
    list_filter = ['log_type', 'member']
    list_display_links = ('id', 'log_type')

    inlines = [MemberLogFieldReadOnlyInline]

class RoomAdmin(admin.ModelAdmin):
    model = Room
    
    list_display = ('id', 'name', 'access')
    list_display_links = ('id', 'name')
    search_fields = ['name', 'access']

    ordering = ("access",)
    filter_horizontal = ('members_with_access', 'members_with_access_removed')

# Register the special models, making them show up in the Django admin panel
admin.site.register(Member, MemberWithLog)
admin.site.register(MemberLog, MemberLogReadOnly)
admin.site.register(Room, RoomAdmin)
