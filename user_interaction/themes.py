from django.templatetags.static import StaticNode
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

class SquireUserTheme:
    """ Base class for user themes """
    name = None
    css = ()
    js = ()

    def get_css(self):
        return format_html_join("\n", "<link rel='stylesheet' href='{}'>", ((StaticNode.handle_simple(x),) for x in self.css))

    def get_js(self):
        return format_html_join("\n", "<script src='{}'></script>", ((StaticNode.handle_simple(x),) for x in self.js))

    def __str__(self):
        return self.name

class DefaultUserTheme(SquireUserTheme):
    """ Standard green-white theme """
    name = "Default"
    css = ('themes/standard-theme.css',)
    js = ('themes/standard-theme.js',)

class DarkUserTheme(SquireUserTheme):
    """ Dark Mode """
    name = "Dark Mode"
    css = ('themes/dark-theme.css',)


THEMES = {
    'THEME_DEFAULT': DefaultUserTheme,
    'THEME_DARK': DarkUserTheme,
}

DEFAULT_THEME = 'THEME_DEFAULT'
