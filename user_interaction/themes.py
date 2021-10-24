from django.templatetags.static import StaticNode
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

class SquireUserTheme:
    """ Base class for user themes """
    name = None
    css = ()
    js = ()
    raw_js = ()

    def get_css(self):
        return format_html_join("\n", "<link rel='stylesheet' href='{}'>", ((StaticNode.handle_simple(x),) for x in self.css))

    def get_js(self):
        return format_html_join("\n", "<script src='{}'></script>", ((StaticNode.handle_simple(x),) for x in self.js))

    def get_raw_js(self):
        return mark_safe(f"<script>{';'.join(self.raw_js)}</script>")

    def __str__(self):
        return self.name

class DefaultUserTheme(SquireUserTheme):
    """ Standard green-white theme """
    name = "Default"
    css = ('themes/standard-theme.css',)

class DarkUserTheme(SquireUserTheme):
    """ Dark Mode """
    name = "Dark Mode"
    css = ('themes/dark-theme.css',)

class AprilUserTheme(SquireUserTheme):
    """ April's Fools 2020 theme """
    name = '"Classic"'
    css = ('themes/april-theme.css',)
    js = ('themes/april-theme.js',)
    raw_js = (
        f"var parrotImg = \"{StaticNode.handle_simple('themes/images/april/parrot.gif')}\"",
        f"var adImg = \"{StaticNode.handle_simple('themes/images/april/tim-merch-ad.gif')}\"",
    )

THEMES = {
    'THEME_DEFAULT': DefaultUserTheme,
    'THEME_DARK': DarkUserTheme,
    'THEME_APRIL': AprilUserTheme,
}

DEFAULT_THEME = 'THEME_DEFAULT'
