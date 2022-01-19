from django.db import models

from membership_file.models import Member
from committees.models import AssociationGroup

from surveys.question_types import question_types



class Survey(models.Model):
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=128)
    created_on = models.DateTimeField(auto_now_add=True)
    organisers = models.ManyToManyField(AssociationGroup, null=True, blank=True)

    def __str__(self):
        return self.name


def get_question_type_choices():
    return [(q_type.type_slug, q_type.type_verbose) for q_type in question_types]


class Question(models.Model):
    name = models.CharField(max_length=16)
    label = models.CharField(max_length=32)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    required = models.BooleanField(default=False)
    type = models.CharField(max_length=8, choices=get_question_type_choices())
    option_1 = models.CharField(max_length=256, blank=True)
    option_2 = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return f'{self.survey}: {self.name}'


class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(auto_now=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.survey}: {self.member}'


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    response = models.ForeignKey(Response, on_delete=models.CASCADE)
    value = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f'{self.question} for response {self.response_id}'
