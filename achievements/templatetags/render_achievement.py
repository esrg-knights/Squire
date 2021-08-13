import urllib

from django import template
from django.contrib.auth.models import User, Group

register = template.Library()

@register.inclusion_tag('achievements/snippets/achievement_external_ref_snippet.html', takes_context=False)
def render_achievement(achievement, display_text=True, **kwargs):
    return {
        'achievement': achievement,
        'display_text': display_text,
        'outline_class': kwargs.get('outline_class', ''),
        'img_height': kwargs.get('img_height', None)
    }
