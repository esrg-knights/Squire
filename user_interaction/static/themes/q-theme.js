"use strict";

// Modify the DOM
$(document).ready(function () {
    console.debug('hello!');
    // Replace 'k' and 'c' by 'q' (leave html between < and > alone)
    replaceInText(document.body, /[kc]+(?![^<]*>)/g, 'q');
    replaceInText(document.body, /[KC]+(?![^<]*>)/g, 'Q');
})
