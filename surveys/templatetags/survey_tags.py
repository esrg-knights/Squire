from django import template

from membership_file.models import Member
from surveys.models import Survey

register = template.Library()


@register.filter
def get_response_of(survey:Survey, member:Member):
    return survey.response_set.filter(member=member).first()

