import itertools
from django.forms import fields


__all__ = ['QuestionType', 'CharQuestion', 'IntQuestion', 'ChoiceQuestion', 'get_question_type']


class QuestionType:
    """
    QuestionTypes are the bridge between the database Question types and the front end visualisation

    Database related parameters:
    type_slug: slugified version for database type storage
    type_verbose: readable name for the question type
    options: - tbd -

    Form related paramters
    formfield_class: The field class for the form
    widget: the widget used for displaying. Defaults to formfield_class default
    """
    formfield_class = None
    type_slug = None
    type_verbose = None
    options = {}
    widget = None

    def __init__(self):
        # Todo: Move to metaclass
        assert self.formfield_class is not None
        assert self.type_slug is not None
        assert self.type_verbose is not None

    def get_form_field(self, question, answer=None):
        """
        Returns the form field instance
        :param question: The question for the form field
        :param answer: The answer instance
        :return:
        """
        return self.formfield_class(
            initial=self.get_field_answer(answer),
            label=question.label,
            widget=self.widget,
            required=question.required,
            **self.get_extra_form_field_kwargs(question, answer=answer)
        )

    def get_extra_form_field_kwargs(self, question, answer=None):
        """
        Additional form field kwargs used for form field initialisation.
        Use this for setting field specific options (such as choices, min_value etc)
        """
        return {
            'validators': self.get_field_validators(question),
        }

    def get_field_validators(self, question):
        """ Returns additional validators """
        return []

    def get_field_answer(self, answer):
        """ Converts db stored answer to answer used for field communication """
        if answer is None:
            return ''
        return answer.value

    def answer_to_db(self, question, value):
        """ Converts the field answer to database ready answer """
        return value


class CharQuestion(QuestionType):
    """ A simple open question """
    formfield_class = fields.CharField
    type_slug = 'CHAR'
    type_verbose = 'Open answer'


class IntQuestion(QuestionType):
    """ An integer question """
    formfield_class = fields.IntegerField
    type_slug = 'INT'
    type_verbose = 'Integer answer'

    def get_extra_form_field_kwargs(self, question, answer=None):
        kwargs = super(IntQuestion, self).get_extra_form_field_kwargs(question, answer=answer)
        if question.option_1:
            kwargs['min_value'] = int(question.option_1)
        if question.option_2:
            kwargs['max_value'] = int(question.option_2)
        return kwargs


class ChoiceQuestion(QuestionType):
    """ A choice question with a dropdown """
    formfield_class = fields.TypedChoiceField
    type_slug = 'CHC'
    type_verbose = 'Choice question'

    def get_extra_form_field_kwargs(self, question, answer=None):
        kwargs = super(ChoiceQuestion, self).get_extra_form_field_kwargs(question, answer=answer)
        # Define the answers in a numbered list of tuples
        kwargs['choices'] = zip(itertools.count(), question.option_1.split(';'))
        # add an empty answer. Make sure the first tuple is an empty string as that invalidates in case it is mandatory
        kwargs['choices'] = [('', '----')] + list(kwargs['choices'])
        return kwargs

    def get_field_answer(self, answer):
        """ Gets the functional field answer from the database
        The communicated field value is NOT the value users see and select. But this value is stored on the database
        for data continuity. So the answer needs to be converted to the correct value
        """
        if answer is None:
            return ''
        # The input initial wants the unique key, not the stringified version of the answer
        options = answer.question.option_1.split(';')
        for i, choice_text in zip(itertools.count(), options):
            if answer.value == choice_text:
                return i
        return None

    def answer_to_db(self, question, value):
        if value == '':
            return ''
        # Convert the answer back from the number to the readable string
        return question.option_1.split(';')[int(value)]


question_types = [CharQuestion, IntQuestion, ChoiceQuestion]


def get_question_type(question):
    """ Given a question, return the initialised questiontype associated with the question """
    for q_type in question_types:
        if question.type == q_type.type_slug:
            return q_type()
    return None
