$(function() {
    $('.enlargable_image').on('click', function() {
        var img_url = $(this).find('img').attr('src');
        if (img_url == null){
            img_url = $(this).attr('data-imgurl');
        }

        $('.imagepreview').attr('src',img_url);
        $('#imagemodal').modal('show');
    });
});
