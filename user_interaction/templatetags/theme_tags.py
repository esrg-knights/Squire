from django import template

from user_interaction.themes import THEMES, DEFAULT_THEME

register = template.Library()

##################################################################################
# Template Tags used for theming
# @since 23 OCT 2021
##################################################################################


@register.simple_tag
def theme_tags(theme):
    theme = theme or DEFAULT_THEME
    theme = THEMES[theme]()
    return theme.get_css() + theme.get_raw_js() + theme.get_js()


@register.filter
def get_theme(user):
    theme = user.preferences.get("layout__theme", None) or DEFAULT_THEME
    return THEMES[theme]()
