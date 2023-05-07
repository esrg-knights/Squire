"use strict";

// Modify the DOM
$(document).ready(function () {
    try {
        console.debug('Q replacement');
        performance.mark('Q-replacement-start');
    } catch (e) {
        console.warn(e);
    }
    // Replace 'k' and 'c' by 'q' (leave html between < and > alone)
    replaceInText(document.body, /(ck|k|c)/g, 'q');
    replaceInText(document.body, /[KC]/g, 'Q');
    try {
        performance.mark('Q-replacement-end');
        performance.measure('Q-replacement', 'Q-replacement-start', 'Q-replacement-end');
    } catch (e) {
        console.warn(e);
    }
})
