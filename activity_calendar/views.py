from django.shortcuts import render

# Front-end route that renders the calendar page
def activity_collection(request): #TODO: Create testcases
    return render(request, 'activity_calendar/calendar.html', {})