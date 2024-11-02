// Modify the DOM
$(document).ready(function () {
    /****************************************************************
     * Generate Navbar Knights rap
     *****************************************************************/
    $(".navbar-nav.mr-auto").append(`
        <li>
            <a class="nav-link" href="https://www.youtube.com/watch?v=1iQzFLO8xeE">Lustrum</a>
        </li>
    `)

    /****************************************************************
     * Generate Cookie Stealing & Parrots
     *****************************************************************/
    $("body").append(`
        <div class="april-footer">
            <p>This website uses cookies to steal your personal data and sells it off to third parties
            such as Quadrivium and Data Analytics for Engineers. Please press Ctrl + W to revoke consent.</p>
        </div>
    `)
    for (let i = 0; i < 70; i++) {
        let offset = i * 30
        if (offset === 2010) {
            offset = 1010
        }
        $("body").append(`
            <img class='april-footer-img' src="${parrotImg}" alt="Party Parrot" style='left: ${offset}px'>
        `)
    }

    /****************************************************************
     * Generate Advertisement
     *****************************************************************/
    var children = $("#mainContent").find("div")
    console.log(children)
    $(children[Math.floor(Math.random() * children.length)]).after(`
        <center>
        <a href="https://timheiszwolf.jimdofree.com/contact/">
            <div class="april-ad left">
                <img src="${adImg}" alt="Tim Heiszwolf Merch Advertisement">
                <p>Advertisement</p>
            </div>
        </a>
        </center>
    `)
});

