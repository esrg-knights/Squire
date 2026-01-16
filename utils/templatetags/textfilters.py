from django import template

register = template.Library()


@register.filter
def endswith(text: str, ends: str):
    return text.endswith(ends)
