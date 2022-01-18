from django.forms import CharField
from django.test import TestCase
from django.forms.widgets import Textarea


from surveys.models import Question, Answer
from surveys.question_types import *


class QuestionTypeTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def setUp(self):
        # Set basic attributes
        class NewQuestionType(QuestionType):
            formfield_class = CharField
            type_slug = 'TEST'
            type_verbose = "Test question type"
            widget = Textarea

        self.question_type = NewQuestionType()
        self.question = Question.objects.get(id=1)
        self.answer = Answer.objects.get(id=1)

    def test_answer_to_db(self):
        self.assertEqual(
            self.question_type.answer_to_db(
                self.question,
                'test answer'
            ),
            'test answer'
        )

    def test_get_field_answer(self):
        self.assertEqual(
            self.question_type.get_field_answer(
                None
            ),
            ''
        )
        # Simple string convertion, no special actions by default
        self.assertEqual(
            self.question_type.get_field_answer(
                self.answer
            ),
            str(self.answer.value)
        )

    def test_get_form_field(self):
        field = self.question_type.get_form_field(self.question)
        self.assertIsInstance(field, CharField)
        self.assertEqual(field.initial, '')
        self.assertEqual(field.label, self.question.label)
        self.assertIsInstance(field.widget, self.question_type.widget)
        self.assertEqual(field.required, self.question.required)


class IntQuestionTypeTest(TestCase):

    def setUp(self):
        self.question_type = IntQuestion()

    def test_get_extra_form_field_kwargs(self):
        question = Question()
        kwargs = self.question_type.get_extra_form_field_kwargs(question)
        self.assertNotIn('min_value', kwargs)
        self.assertNotIn('max_value', kwargs)

        question = Question(option_1=2, option_2=12)
        kwargs = self.question_type.get_extra_form_field_kwargs(question)
        self.assertEqual(kwargs['min_value'], 2)
        self.assertEqual(kwargs['max_value'], 12)


class ChoiceQuestionTypeTest(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def setUp(self):
        self.question_type = ChoiceQuestion()

    def test_get_extra_form_field_kwargs(self):
        question = Question(option_1='One;22;number three')
        kwargs = self.question_type.get_extra_form_field_kwargs(question)
        self.assertEqual(len(kwargs['choices']), 4)
        self.assertEqual(kwargs['choices'][0][0], '', msg="First list entry should have empty string as key")
        self.assertEqual(kwargs['choices'][3][1], 'number three')

    def test_get_field_answer(self):
        answer = Answer(question=Question(option_1='One;22;number three'), value='number three')
        field_answer = self.question_type.get_field_answer(answer)
        self.assertEqual(field_answer, 2)

    def test_answer_to_db(self):
        answer = self.question_type.answer_to_db(
            Question(option_1='One;22;number three'),
            '1'
        )
        self.assertEqual(answer, '22')

