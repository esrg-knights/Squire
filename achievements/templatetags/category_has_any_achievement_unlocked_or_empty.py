from django import template

register = template.Library()

##################################################################################
# Template Tag that checks whether any achievement in a given category has been unlocked
# @since 30 MAR 2020
##################################################################################


@register.filter
def category_has_any_achievement_unlocked_or_empty(category):
    # Retrun True if the category is empty
    if not category.get('achievements'):
        return True

    # Otherwise iterate over all the category's achievements
    for achievement in category.get('achievements'):
        if achievement.get('claimants'):
            return True
    return False
