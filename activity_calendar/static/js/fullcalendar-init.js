// Initalises FullCalendar
document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'en-gb', // We want dd/mm/yyy formatting
        firstDay: 1, // Weeks start on monday
        nowIndicator: true,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false, // AM/PM display
        },
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,dayGridMonth listWeek,listMonth'
        },
        // Determines how far forward the scroll pane is initially scrolled.
        // This value ensures that evening-activities are visible without needing to scroll
        scrollTime: '14:00:00',
        // customize the button names,
        // otherwise they'd all just say "list"
        views: {
            listWeek: { buttonText: 'list week' },
            listMonth: { buttonText: 'list month' }
        },
        editable: false,
        navLinks: false, // can click day/week names to navigate views
        dayMaxEvents: true, // allow "more" link when too many events
        events: {
            url: '/api/calendar/fullcalendar',
            failure: function() {
                if ($("#error-msg .alert").length <= 1) {
                    $("#error-template").clone().appendTo("#error-msg").show();
                }
            },
            success: function(response){
                console.log('Activities were successfully fetched!')
            },
            // extraParams: {
            //     test: 'hi!',
            // },
        },
        // FullCalendar expects a JSON array, which is part of a JSON object of us
        eventSourceSuccess: function(content, xhr) {
            return content.activities;
        },
        eventClick: function(info) {
            onEventClick(info, this)
        },
        loading: function(bool) {
            document.getElementById('loading').style.display =
                bool ? 'block' : 'none';
        }
    });
    calendar.render();
});


function onEventClick(info, calendar) {
    var event = info.event
    var start_date = event.start
    var end_date = event.end

    var date_str = ""
    if (start_date.getDate() === end_date.getDate()
            && start_date.getMonth() === end_date.getMonth()
            && start_date.getFullYear() === end_date.getFullYear()) {
        
        // Vrijdag, 7 augustus 19:00 – 22:00
        date_str = start_date.toLocaleString('en-gb', {
                weekday: 'long', month: 'long', day: 'numeric' 
            })

        if (event.allDay) {
            // All-day event; display "all day" instead of event duration
            date_str += ' - ' + calendar.currentData.options.allDayText
        } else {
            date_str += ' '
                + start_date.toLocaleString('en-gb', {
                    hour: 'numeric', minute: 'numeric' 
                })
                + ' - '
                + end_date.toLocaleString('en-gb', {hour: 'numeric', minute: 'numeric'})
        }
    } else {
        // 5 augustus, 19:30 – 6 augustus, 02:00
        var opts = {}

        if (!event.allDay) {
            opts = {hour: 'numeric', minute: 'numeric'}
        }

        date_str = start_date.toLocaleString('en-gb', {
            month: 'long', day: 'numeric', ...opts
        })
        date_str += ' - ' + end_date.toLocaleString('en-gb', {
            month: 'long', day: 'numeric', ...opts
        })
    }

    var rInfo = event.extendedProps.recurrenceInfo

    // Set modal contents
    $('#modal-title').text(event.title)
    $('#event-date').text(date_str)
    if (rInfo.rrules.length !== 0) {
        $('#event-recurrence-info #rrules').text('Repeats ' + rInfo.rrules.join(' and '))
    }
    if (rInfo.rdates.length !== 0) {
        $('#event-recurrence-info #rdates').text('Also on: ' + rInfo.rdates.join(' and ') )
    }
    if (rInfo.exrules.length !== 0) {
        $('#event-recurrence-info #exrules').text('Excluding ' + rInfo.exrules.join(' and '))
    }
    if (rInfo.exdates.length !== 0) {
        $('#event-recurrence-info #exdates').text('Except on: ' + rInfo.exdates.join(' and '))
    }
    $('#event-location').text(event.extendedProps.location)
    $('#event-description').text(event.extendedProps.description)
    
    if (event.extendedProps.isSubscribed) {
        $('#subscribe-required').hide()
        $('#subscribe-done').show()
        $('#event-subscription').text("You are registered for this activity!")
    } else if (event.extendedProps.subscriptionsRequired) {
        $('#subscribe-required').show()
        $('#subscribe-done').hide()
        $('#event-subscription').text("You need to register for this activity before you can join!")
    }

    if (!event.extendedProps.canSubscribe) {
        $('#event-subscription-closed').text("Registrations have not opened yet or are closed.")
    }
    
    if (event.extendedProps.maxParticipants === -1) {
        $('#event-participants-count').text(`${event.extendedProps.numParticipants} participant(s) so far.`)
    } else {
        $('#event-participants-count').text(`${event.extendedProps.numParticipants}/${event.extendedProps.maxParticipants} participant(s)`)
    }

    // Link to the correct occurence
    $('#event-subscribe-url').attr("href", `calendar/slots/${event.groupId}?date=${encodeURIComponent(start_date.toISOString())}`)

    $('#event-modal').modal()
}
