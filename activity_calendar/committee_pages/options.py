from committees.options import SimpleFormSettingsOption

from activity_calendar.committee_pages.forms import GroupMeetingSettingsForm


class MessageOptions(SimpleFormSettingsOption):
    order = 8
    display_title = "Meeting calendar settings"
    display_text = (
        "Adjust settings how the meetings for this group are displayed when imported in the calendar. "
        "Note: It may take up to 24 hours for your calendar to process these changes."
    )
    name = "Meetings"
    option_form_class = GroupMeetingSettingsForm
    url_keyword = "meetings"
