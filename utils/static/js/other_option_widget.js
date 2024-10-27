// Wait for the document to load
window.addEventListener('load', function () {
    const optionWidgets = this.document.querySelectorAll("div.other-option-widget")
    // Find all radio-other widgets
    for (var i = 0; i < optionWidgets.length; i++) {
        const widget = optionWidgets[i]
        // Fetch elements
        const otherRad = widget.querySelector(".radiolist > div:last-child input:first-child")
        const otherInput = widget.querySelectorAll(".radiolist > div:last-child input:not(:first-child)")
        const rads = widget.querySelectorAll(".radiolist > div:not(:last-child) input")
        // Disable the free text field
        const disableInput = () => {
            for (var i = 0; i < otherInput.length; i++) {
                otherInput[i].disabled = true;
            }
        }
        // Enable the free text field
        const enableInput = () => {
            for (var i = 0; i < otherInput.length; i++) {
                otherInput[i].disabled = false;
            }
        }
        // Add listeners that (de)activate the enable/disable methods
        for (var j = 0; j < rads.length; j++) {
            rads[j].addEventListener('change', disableInput)
        }
        otherRad.addEventListener('change', enableInput)
    }
})
