from django.forms import Form
from django.utils.text import slugify

from .models import Answer, Response
from.question_types import get_question_type


class SurveyForm(Form):

    def __init__(self, *args, survey=None, response:Response=None, **kwargs):
        assert survey is not None
        assert response is not None
        assert response.survey == survey
        super(SurveyForm, self).__init__(*args, **kwargs)

        # Create question fields
        for question in survey.question_set.all():
            if response:
                answer =  response.answer_set.filter(question=question).first()
            else:
                answer = None
            self.fields[slugify(question.name)] = get_question_type(question).get_form_field(question=question, answer=answer)

        self.survey = survey
        self.response = response

    def save(self):
        # Make sure this is done first in case the response is not yet present on the database
        self.response.save()

        for question in self.survey.question_set.all():
            try:
                answer = Answer.objects.get(
                    response=self.response,
                    question=question,
                )
            except Answer.DoesNotExist:
                answer = Answer(response=self.response, question=question)

            # Get the db ready answer (this could vary for special types such as choice questions)
            question_type = get_question_type(question)
            answer.value = question_type.answer_to_db(question, self.cleaned_data[slugify(question.name)])

            answer.save()

