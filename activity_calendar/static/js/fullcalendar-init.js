// Initalises FullCalendar
document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'en-gb', // We want dd/mm/yyy formatting
        firstDay: 1, // Weeks start on monday
        nowIndicator: true,
        allDaySlot: false, // We don't have All Day slots at the moment, disable this bar
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false, // AM/PM display
        },
        initialView: $(window).width() < 992 ? 'listWeek' : 'dayGridMonth',
        customButtons: {
            importCalendar: {
                text: 'Import this Calendar',
                click: function() {
                    $('#importModal').modal('show')
                },
            }
        },
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,dayGridMonth listWeek,listMonth importCalendar'
        },
        // Determines how far forward the scroll pane is initially scrolled.
        // This value ensures that evening-activities are visible without needing to scroll
        scrollTime: '14:30:00',
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
    $("#copy-calendar-url-to-clipboard").click(onCalendarCopyClick)
});

function onCalendarCopyClick() {
    // Copy the calendar URL to the clipboard
    navigator.clipboard.writeText($("#calendar-url").text().trim());
}

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
        date_str = start_date.toLocaleString('en-gb', {
            month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric',
        })
        date_str += ' - ' + end_date.toLocaleString('en-gb', {
            month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric',
        })
    }

    var rInfo = event.extendedProps.recurrenceInfo
    var recurrence_date = new Date(event.extendedProps.recurrence_id)

    // Set modal contents
    $('#modal-title').text(event.title)
    $('#event-date').text(date_str)

    // Add a small notice if this occurrence takes place on a different day than
    //  its recurrence indicates. I.e., this occurrence has an alternative start date
    if (start_date.getDate() !== recurrence_date.getDate()
            || start_date.getMonth() !== recurrence_date.getMonth()
            || start_date.getFullYear() !== recurrence_date.getFullYear()) {

        date_str = recurrence_date.toLocaleString('en-gb', {
            weekday: 'long', month: 'long', day: 'numeric'
        })

        if (event.allDay) {
            // All-day event; display "all day" instead of event duration
            date_str += ' (' + calendar.currentData.options.allDayText + ')'
        } else {
            date_str += ' ('
                + recurrence_date.toLocaleString('en-gb', {
                    hour: 'numeric', minute: 'numeric'
                })
                + ')'
        }
        $('#occurrence-replacement').text("Replacement for " + date_str)
    } else {
        $('#occurrence-replacement').text("")
    }

    if (rInfo.rrules.length !== 0) {
        $('#event-recurrence-info #rrules').text('Repeats ' + rInfo.rrules.join(' and '))
    } else {
        $('#event-recurrence-info #rrules').text("")
    }


    if (rInfo.rdates.length !== 0) {
        $('#event-recurrence-info #rdates').text('Also on: ' + rInfo.rdates.join(' and ') )
    } else {
        $('#event-recurrence-info #rdates').text("")
    }

    if (rInfo.exrules.length !== 0) {
        $('#event-recurrence-info #exrules').text('Excluding ' + rInfo.exrules.join(' and '))
    } else {
        $('#event-recurrence-info #exrules').text("")
    }

    if (rInfo.exdates.length !== 0) {
        $('#event-recurrence-info #exdates').text('Except on: ' + rInfo.exdates.join(' and '))
    } else {
        $('#event-recurrence-info #exdates').text("")
    }

    $('#event-location').text(event.extendedProps.location)
    $('#event-description').html(event.extendedProps.description)
    martorhljs('#event-description') // Update code block highlighting

    if (event.extendedProps.isSubscribed) {
        $('#subscribe-required').hide()
        $('#subscribe-done').show()
        $('#subscribe-info').hide()
        $('#event-subscription').text("You are registered for this activity!")
    } else if (event.extendedProps.subscriptionsRequired) {
        $('#subscribe-required').show()
        $('#subscribe-done').hide()
        $('#subscribe-info').hide()
        $('#event-subscription').text("You need to register for this activity before you can join!")
    } else {
        $('#subscribe-required').hide()
        $('#subscribe-done').hide()
        $('#subscribe-info').show()
        $('#event-subscription').text("")
    }

    if (!event.extendedProps.canSubscribe) {
        $('#event-subscription-closed').text("Registrations have not opened yet or are closed.")
    } else {
        $('#event-subscription-closed').text("")
    }

    if (event.extendedProps.maxParticipants === -1) {
        $('#event-participants-count').text(`${event.extendedProps.numParticipants} participant(s) so far.`)
    } else {
        $('#event-participants-count').text(`${event.extendedProps.numParticipants}/${event.extendedProps.maxParticipants} participant(s)`)
    }

    // Link to the correct occurence
    $('#event-subscribe-url').attr("href", `${event.extendedProps.urlLink}`)

    $('#event-modal').modal()
}
