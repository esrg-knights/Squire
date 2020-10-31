from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def activity_default_value(context, field_name):
    """ Returns the activity value for the given activity_moment field_name """
    # Strip the standard start of the local names in the activitymoment

    field_name = field_name[len('local_'):]
    activity = context['activity_moment'].parent_activity
    return getattr(activity, field_name)
