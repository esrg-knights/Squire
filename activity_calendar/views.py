from django.shortcuts import render


# Front-end route that renders the calendar page
def activity_collection(request): #pragma: no cover (This was an example page-render included for reference; tests should be created later)
    return render(request, 'activity_calendar/calendar.html', {})