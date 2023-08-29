from django.templatetags.static import StaticNode
from django.test import TestCase

from user_interaction.themes import SquireUserTheme


class DummyUserTheme(SquireUserTheme):
    """Dummy theme used for testing"""

    name = "Dummy"
    css = ("css1.css", "css2.css")
    js = ("js1.js",)
    raw_js = (
        f"var img1 = \"{StaticNode.handle_simple('mystaticfile.png')}\"",
        "var x = 1 + 41",
    )


class SquireUserThemeTest(TestCase):
    """Tests output of a SquireUserTheme"""

    def setUp(self):
        self.theme = DummyUserTheme()

    def test_css(self):
        """Tests if CSS files are included properly"""
        css = self.theme.get_css()
        self.assertHTMLEqual(
            css, "<link rel='stylesheet' href='/static/css1.css'><link rel='stylesheet' href='/static/css2.css'>"
        )

    def test_js(self):
        """Tests if JS files are included properly"""
        js = self.theme.get_js()
        self.assertHTMLEqual(js, "<script src='/static/js1.js'></script>")

    def test_raw_js(self):
        """Tests if raw JS is included properly"""
        js = self.theme.get_raw_js()
        self.assertEqual(js, '<script>var img1 = "/static/mystaticfile.png";var x = 1 + 41</script>')
