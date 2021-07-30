
from utils.forms import get_basic_filter_by_field_form


class SearchFormMixin:
    """ A mixin for ListViews that allow filtering of the data in the queryset through a form """
    search_form_class = None
    filter_field_name = None

    def get_filter_form(self):
        """ Returns the initialised filter form """
        if self.filter_field_name:
            form_class = get_basic_filter_by_field_form(self.filter_field_name)
        elif self.search_form_class:
            form_class = self.search_form_class
        else:
            raise KeyError("Either 'search_form_class' or a 'filter_field_name' need to be defined"
                           "to use SearchFormMixin")
        return form_class(self.request.GET)

    def dispatch(self, request, *args, **kwargs):
        self.search_form = self.get_filter_form()
        return super(SearchFormMixin, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(SearchFormMixin, self).get_queryset()
        return self.filter_data(queryset)

    def filter_data(self, queryset):
        if self.search_form.is_valid():
            return self.search_form.get_filtered_items(queryset)
        else:
            return queryset

    def get_context_data(self, **kwargs):
        return super(SearchFormMixin, self).get_context_data(
            filter_form=self.search_form,
            **kwargs
        )
