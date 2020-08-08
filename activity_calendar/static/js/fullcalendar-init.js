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
            url: 'fullcalendar/',
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
        loading: function(bool) {
        document.getElementById('loading').style.display =
            bool ? 'block' : 'none';
        }
    });
    calendar.render();
});
