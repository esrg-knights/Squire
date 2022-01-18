from django.contrib.admin import site, ModelAdmin, register
from django.contrib import admin


from surveys.models import Survey, Question, Response, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@register(Survey)
class SurveyAdmin(ModelAdmin):
    list_display = ('id', 'name', 'current_reply_count')
    list_display_links = ('id', 'name',)

    inlines = [QuestionInline]

    @staticmethod
    def current_reply_count(obj):
        return obj.response_set.count()
    current_reply_count.short_description = 'Number of responses'


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@register(Response)
class ResponseAdmin(ModelAdmin):
    list_display = ('survey', 'member')
    list_display_links = ('survey', 'member')
    list_filter = ('survey', 'last_updated_on')
    inlines = [AnswerInline]


@register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ('survey', 'name', 'type')
    list_display_links = ('survey', 'name')
    list_filter = ('survey', 'required')
