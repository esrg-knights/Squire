from django import template
from martor.widgets import get_theme

register = template.Library()

##################################################################################
# Template Tags to include files needed when rendering Markdown without having
#   Martor's widget active on the same page.
# @since 05 AUG 2021
##################################################################################

@register.inclusion_tag('core/martor/martor_render_js.html')
def martor_render_js(import_hljs=True, invoke_hljs_method=False, method_param=None):
    """
        Template tag that includes the neccesary JS needed for Markdown to be rendered
        when Martor's widget isn't active on the same page.
    """
    return {
        'import_hljs': import_hljs,
        'invoke_hljs_method': invoke_hljs_method,
        'method_param': method_param,
    }


_martor_theme = get_theme()

@register.inclusion_tag('core/martor/martor_render_css.html')
def martor_render_css():
    """
        Template tag that includes the neccesary CSS needed for Markdown to be rendered
        when Martor's widget isn't active on the same page.
    """
    return {
        'martor_theme': _martor_theme
    }
