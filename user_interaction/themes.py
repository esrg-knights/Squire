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

class LightUserTheme(SquireUserTheme):
    """ Standard green-white theme """
    name = "Light theme"
    css = ('themes/standard-theme.css',)

class DarkUserTheme(SquireUserTheme):
    """ Dark Mode """
    name = "Dark Mode"
    css = LightUserTheme.css + ('themes/dark-theme.css',) #here, so it's consistent 

class DefaultAutoTheme(SquireUserTheme):
    name = "Automatically switch between dark and light"
    css = ("themes/auto.css",)

class AprilUserTheme(SquireUserTheme):
    """ April's Fools 2020 theme """
    name = '"Classic"'
    css = ('themes/april-theme.css',)
    js = ('themes/april-theme.js',)
    raw_js = (
        f"var parrotImg = \"{StaticNode.handle_simple('themes/images/april/parrot.gif')}\"",
        f"var adImg = \"{StaticNode.handle_simple('themes/images/april/tim-merch-ad.gif')}\"",
    )

class FantasyCourtUserTheme(SquireUserTheme):
    """ Fantasy Court theme """
    name = 'Fantasy Court'
    css = ('themes/fc-theme.css',)
    js = ('themes/fc-theme.js',)
    raw_js = (
        f"var fancyedgeImg = \"{StaticNode.handle_simple('themes/images/fc/fancy-edge.png')}\"",
    )

class QuadriviumUserTheme(SquireUserTheme):
    """ Quadrivium Theme """
    name = 'Nemesis'
    css = ('themes/q-theme.css',)
    js = ('themes/q-theme.js',)

class DoppioUserTheme(SquireUserTheme):
    """ Doppio Theme """
    name = 'Espresso'
    css = ('themes/doppio-theme.css',)

class ScalaUserTheme(SquireUserTheme):
    """ Scala Theme """
    name = 'Dining'
    css = ('themes/scala-theme.css',)

THEMES = {
    'THEME_DEFAULT': DefaultAutoTheme,
    'THEME_LIGHT': LightUserTheme,
    'THEME_DARK': DarkUserTheme,
    'THEME_APRIL': AprilUserTheme,
    'THEME_FC': FantasyCourtUserTheme,
    'THEME_Q': QuadriviumUserTheme,
    'THEME_DOPPIO': DoppioUserTheme,
    'THEME_SCALA': ScalaUserTheme,
}

DEFAULT_THEME = 'THEME_DEFAULT'
