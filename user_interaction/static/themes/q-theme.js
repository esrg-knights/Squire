// Modify the DOM
$( document ).ready(function() {
    console.debug('hello!')
    let html = $('body main').html()
    // Replace 'k' and 'c' by 'q' (leave html between < and > alone)
    html = html.replace(/[kc]+(?![^<]*>)/g, 'q')
    html = html.replace(/[KC]+(?![^<]*>)/g, 'Q')
    $('body main').html(html)
})
