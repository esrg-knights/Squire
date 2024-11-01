from datetime import datetime

from django.contrib import admin, messages
from django_object_actions import DjangoObjectActions, action as object_action
from import_export.admin import ExportActionMixin
from import_export.forms import ExportForm
from import_export.formats.base_formats import CSV, ODS, TSV, XLSX

from core.admin import DisableModificationsAdminMixin, URLLinkInlineAdminMixin
from membership_file.forms import AdminMemberForm
from membership_file.export import MemberResource, MembersFinancialResource
from membership_file.models import Member, MemberLog, MemberLogField, Room, MemberYear, Membership
from membership_file.views import RegisterNewMemberAdminView, ResendRegistrationMailAdminView
from utils.forms import RequestUserToFormModelAdminMixin


class TSVUnicodeBOM(TSV):
    """.tsv that starts with a `ZERO WIDTH NO-BREAK SPACE`, which is a Byte Order Marker, which forces Excel to recognise it as Unicode.
    More info: https://en.wikipedia.org/w/index.php?title=Byte_order_mark&oldid=1135118973#Usage"""

    def export_data(self, *args, **kwargs):
        return "\N{ZERO WIDTH NO-BREAK SPACE}" + super().export_data(*args, **kwargs)


class HideRelatedNameAdmin(admin.ModelAdmin):
    class Media:
        # Hacky solution to hide the "X was updated: <Y> -> <Z>" text
        # We don't need to edit this information anyways, so it's safe to hide
        # https://stackoverflow.com/a/5556813
        css = {
            "all": ("css/hide_related_model_name.css",),
        }


class RoomInline(admin.TabularInline):
    model = Room.members_with_access.through
    extra = 0


class MemberYearInline(admin.TabularInline):
    model = Membership
    fk_name = "member"
    extra = 0
    fields = ["year", "has_paid", "payment_date"]


class MemberLogReadOnlyInline(DisableModificationsAdminMixin, URLLinkInlineAdminMixin, admin.TabularInline):
    model = MemberLog
    extra = 0
    readonly_fields = ["date", "get_url"]
    fields = ["log_type", "user", "date", "get_url"]
    ordering = ("-date",)

    # Whether the object can be deleted inline
    can_delete = False


@admin.register(Member)
class MemberWithLog(RequestUserToFormModelAdminMixin, DjangoObjectActions, ExportActionMixin, HideRelatedNameAdmin):
    ##############################
    #  Export functionality
    resource_classes = [MemberResource]
    export_form_class = ExportForm
    formats = (CSV, XLSX, TSV, ODS)

    @object_action(attrs={"class": "addlink"})
    def register_new_member(modeladmin, request, queryset):
        view = modeladmin.admin_site.admin_view(RegisterNewMemberAdminView.as_view(model_admin=modeladmin))
        return view(request)

    @object_action(label="Re-send registration email", description="Re-sends the registration email to this member.")
    def resend_verification(self, request, object):
        view = self.admin_site.admin_view(ResendRegistrationMailAdminView.as_view(model_admin=self))
        return view(request, pk=object.pk)

    # Note: get_urls is extended
    changelist_actions = ("register_new_member",)
    change_actions = ("resend_verification",)

    def get_change_actions(self, request, object_id, form_url):
        # Action is only available if the user can add members normally
        actions = super().get_change_actions(request, object_id, form_url)
        if (
            not request.user.has_perm("membership_file.add_member")
            or Member.objects.get(id=object_id).user is not None
        ):
            actions = [action for action in actions if action != "resend_verification"]
        return actions

    def get_changelist_actions(self, request):
        # Action is only available if the user can add members normally
        actions = super().get_changelist_actions(request)
        if not request.user.has_perm("membership_file.add_member"):
            actions = [action for action in actions if action != "register_new_member"]
        return actions

    def has_export_permission(self, request):
        return request.user.has_perm("membership_file.can_export_membership_file")

    def get_export_filename(self, request, queryset, file_format):
        filename_prefix = ""
        if queryset.filter(is_deregistered=True).exists():
            filename_prefix = "HAS_DEREGISTERED_MEMBERS-"

        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = "%sMembershipFile-%s.%s" % (filename_prefix, date_str, file_format.get_extension())

        return filename

    ##############################
    form = AdminMemberForm
    save_on_top = True

    list_display = (
        "id",
        "user",
        "first_name",
        "tussenvoegsel",
        "last_name",
        "educational_institution",
        "is_deregistered",
        "marked_for_deletion",
    )
    list_filter = [
        "memberyear",
        "is_deregistered",
        "marked_for_deletion",
        "is_honorary_member",
        "educational_institution",
        ("tue_card_number", admin.EmptyFieldListFilter),
        ("external_card_number", admin.EmptyFieldListFilter),
        ("key_id", admin.EmptyFieldListFilter),
        ("phone_number", admin.EmptyFieldListFilter),
    ]
    list_display_links = ("id", "user", "first_name")
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "tue_card_number",
        "external_card_number",
        "key_id",
    ]
    search_help_text = "Search for name, email, phone number, TUe/external card number, key ID"

    readonly_fields = ["last_updated_by", "last_updated_date"]

    # Display a search box instead of a dropdown menu
    autocomplete_fields = ["user"]

    # fmt: off
    fieldsets = [
        (None, {'fields':
            ['user', ('first_name', 'tussenvoegsel', 'last_name'),
            'marked_for_deletion',
            ('last_updated_date', 'last_updated_by'),]}),
        ('Membership Status', {'fields':
            ['is_deregistered', 'is_honorary_member', 'member_since']}),
        ('Contact Details', {'fields':
            ['email', 'phone_number',
            ('street', 'house_number', 'house_number_addition'), ('postal_code', 'city'), 'country']}),
        ('Room Access', {'fields':
            ['key_id', 'tue_card_number',
            ('external_card_number', 'external_card_digits'),
            'external_card_deposit', 'accessible_rooms']}),
        ('Legal Information', {'fields':
            ['educational_institution', 'student_number',
            'date_of_birth', 'legal_name']}),
        ('Notes', {'fields':
            ['notes']}),
    ]
    # fmt: on

    inlines = [MemberLogReadOnlyInline, MemberYearInline]

    # Show at most 150 members per page (opposed to 100).
    # Show a "show all" button if <999 members are selected (opposed to 200)
    #   We're increasing these numbers as the board needs to be able to select all members in
    #   order to export & send emails to them. We likely won't go over 150 members, so this
    #   basically gets rid of any chances of forgetting to click the "select all" button,
    #   causing the last few members to not receive emails.
    list_per_page = 150
    list_max_show_all = 999

    actions = ["mark_as_current_member", ExportActionMixin.export_admin_action]

    # Disable bulk delete
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def mark_as_current_member(self, request, queryset):
        try:
            year = MemberYear.objects.get(is_active=True)
        except MemberYear.MultipleObjectsReturned:
            self.message_user(
                request, "There are multiple years active,  only  one should be active", level=messages.ERROR
            )
            return
        except MemberYear.DoesNotExist:
            self.message_user(
                request, "There is currently no year active, make sure that one is active", level=messages.ERROR
            )
            return
        created_count = 0
        for member in queryset:
            member, created = Membership.objects.get_or_create(
                member=member,
                year=year,
            )
            created_count += int(created)

        self.message_user(
            request,
            f"Succesfully created {created_count} new members. {queryset.count() - created_count} instances were already a member",
            level=messages.SUCCESS,
        )

    mark_as_current_member.short_description = "Assign as member of the currently active year"

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


# Prevents MemberLogField creation, editing, or deletion in the Django Admin Panel
class MemberLogFieldReadOnlyInline(DisableModificationsAdminMixin, admin.TabularInline):
    model = MemberLogField
    extra = 0

    # Whether the object can be deleted inline
    can_delete = False


# Prevents MemberLog creation, edting, or deletion in the Django Admin Panel
@admin.register(MemberLog)
class MemberLogReadOnly(DisableModificationsAdminMixin, HideRelatedNameAdmin):
    # Show the date at which the information was updated as well
    readonly_fields = ["date"]
    list_display = ("id", "log_type", "user", "member", "date")
    list_filter = ["log_type", "member"]
    list_display_links = ("id", "log_type")

    inlines = [MemberLogFieldReadOnlyInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    model = Room

    list_display = ("id", "name", "room_number", "access_type", "access_specification")
    list_display_links = ("id", "name")
    search_fields = ["name", "room_number"]
    search_help_text = "Search for name, room number"
    ordering = ("access_type", "access_specification")
    filter_horizontal = ("members_with_access",)

    fieldsets = [
        (
            None,
            {
                "fields": [
                    (
                        "name",
                        "room_number",
                    ),
                    ("access_type", "access_specification"),
                    "notes",
                    "members_with_access",
                ]
            },
        ),
    ]


@admin.register(MemberYear)
class MemberYearAdmin(ExportActionMixin, admin.ModelAdmin):
    ##############################
    #  Export functionality
    resource_classes = [MembersFinancialResource]
    export_form_class = ExportForm
    formats = (CSV, XLSX, TSV, ODS)

    def has_export_permission(self, request):
        return request.user.has_perm("membership_file.can_export_membership_file")

    def get_export_filename(self, request, queryset, file_format):
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = "YearSubscriptions-%s.%s" % (date_str, file_format.get_extension())
        return filename

    def get_data_for_export(self, request, queryset, *args, **kwargs):
        queryset = Membership.objects.filter(year__in=queryset)
        return super(MemberYearAdmin, self).get_data_for_export(request, queryset, *args, **kwargs)

    ##############################

    list_display = ["name", "is_active", "member_count"]
    list_filter = [
        "is_active",
    ]

    def member_count(self, obj):
        return obj.members.count()


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["member", "year", "has_paid", "payment_date"]
    list_filter = ["year", "has_paid"]
