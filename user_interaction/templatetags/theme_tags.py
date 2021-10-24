from django import template
from django.utils.safestring import mark_safe

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
