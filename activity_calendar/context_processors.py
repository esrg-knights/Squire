from activity_calendar.constants import ActivityStatus, ActivityType, SlotCreationType


# Allow these globals to be fetched in ALL templates by adding them as a context processor in TEMPLATES in settings.py
def activity_types(request):
    return {"ActivityType": ActivityType}


def slot_creation_types(request):
    return {"SlotCreationType": SlotCreationType}


def activity_statuses(request):
    return {"ActivityStatus": ActivityStatus}
