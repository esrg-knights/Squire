from django import forms



def get_basic_filter_by_field_form(field_name):
    class FilterByFieldForm(forms.Form):
        search_field = forms.CharField(max_length=100, required=False, label=field_name)

        def get_filtered_items(self, queryset):
            return queryset.filter(name__icontains=self.cleaned_data['search_field']).order_by(field_name)

    return FilterByFieldForm
