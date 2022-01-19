from django import template

from membership_file.models import Member
from surveys.models import Survey, Question, Response

register = template.Library()


@register.filter
def get_response_of(survey:Survey, member:Member):
    return survey.response_set.filter(member=member).first()


@register.filter()
def get_answer_of(question: Question, response: Response):
    """
    Returns the string answer of a question in a certain response
    :param question: The question instance
    :param response: The response instance
    :return: string representing the answer to a question
    """
    return getattr(question.answer_set.filter(response=response).first(), 'value', None)
