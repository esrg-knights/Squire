from django.contrib import admin
from .models import Member, MemberLog, MemberLogField
from django.contrib import admin

# Ensures that the last_updated_by field is also updated properly from the Django admin panel
class MemberWithLog(admin.ModelAdmin):
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

# Prevents MemberLog creation, edting, or deletion in the Django Admin Panel
class MemberLogReadOnly(admin.ModelAdmin):
    # Show the date at which the information was updated as well
    readonly_fields = ['date']

    # Disable creation
    def has_add_permission(self, request):
        return False
    
    # Disable editing
    def has_change_permission(self, request, obj=None):
        return False

    # Disable deletion
    def has_delete_permission(self, request, obj=None):
        return False

# Prevents MemberLogField creation, edting, or deletion in the Django Admin Panel
class MemberLogFieldReadOnly(admin.ModelAdmin):
    # Disable creation
    def has_add_permission(self, request):
        return False
    
    # Disable editing
    def has_change_permission(self, request, obj=None):
        return False

    # Disable deletion
    def has_delete_permission(self, request, obj=None):
        return False

# Register the special models, making them show up in the Django admin panel
admin.site.register(Member, MemberWithLog)
admin.site.register(MemberLog, MemberLogReadOnly)
admin.site.register(MemberLogField, MemberLogFieldReadOnly)