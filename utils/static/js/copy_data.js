

function copy_data_to_clipboard(element) {
    // Copy the calendar URL to the clipboard
    var data = $(element).data('copy');
    navigator.clipboard.writeText(data);
    $(element).popover({
        trigger: 'focus',
        placement: "bottom"
    });

    $(element).popover('show');
}

$("[data-copy]").click(function(event){
    var element = $(event.target);
    copy_data_to_clipboard(element);
});
