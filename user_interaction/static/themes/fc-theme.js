// Modify the DOM
$(document).ready(function () {
    $("html").append("<div class='fancy-edge fancy-edge-left'></div><div class='fancy-edge fancy-edge-right'></div>")
    $(".fancy-edge").css("background-image", "url(" + fancyedgeImg + ")")
})
