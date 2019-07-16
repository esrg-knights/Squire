from django.contrib import admin
from .models import Member, MemberLog, MemberLogField
from django.contrib import admin

# Ensures that the last_updated_by field is also updated properly from the Django admin panel
class MemberWithLog(admin.ModelAdmin):
    # Show the date and user that last updated the member
    readonly_fields = ['last_updated_by', 'last_updated_date']

    # Override the admin panel's save method to automatically include the user that updated the member
    def save_model(self, request, obj, form, change):
        obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)

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