from typing import List, Type
from django.forms import RadioSelect, TextInput
from django.forms.widgets import Widget


class OtherRadioSelect(RadioSelect):
    """
    A widget containing radio inputs as well as an "Other" option that
    is another widget, such as a free text widget.

    This can be useful to provide a preset of commonly used selections, such as
    a list of common educational institutions.
    """

    template_name = "utils/snippets/otherradio.html"

    # Input type for "other" option
    other_widget_class: Type[Widget] = TextInput
    # Field name used for the "other" option in the group of radio buttons
    other_option_name = "_OTHER"
    # Field name for the other widget
    other_field_name = "%s__other"

    class Media:
        js = ("js/other_option_widget.js",)

    def __init__(self, attrs=None, choices=None) -> None:
        if attrs is None or attrs.get("class", None) is None:
            attrs = attrs or {}
            attrs["class"] = "radiolist"
        super().__init__(attrs, choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # If an initial value was provided that does not occur in the list,
        #   set it as the initial value of the "other" field widget
        # If an initial value was provided that DOES occur in the list,
        #   disable the "other" field widget by default
        context["other_widget"] = self.other_widget_class().get_context(
            self.other_field_name % name,
            "" if self.any_selected else value,
            {**self.attrs, **(attrs or {}), **{"disabled": self.any_selected}},
        )["widget"]
        return context

    def value_from_datadict(self, data, files, name):
        # When fetching the results, if the 'other' option was selected,
        #   instead fetch the result from the other widget.
        value = super().value_from_datadict(data, files, name)
        if value == self.other_option_name:
            return data.get(self.other_field_name % name)
        return value

    def optgroups(self, name: str, value: List[str], attrs=None):
        # Add the 'Other' option to the list of options
        self.any_selected = False
        optgroups = super().optgroups(name, value, attrs)

        option = self.create_other_option(
            name,
            self.other_option_name,
            "Other:",
            not self.any_selected,
            len(self.choices),
            subindex=None,
            attrs=attrs,
        )
        optgroups.append((None, [option], len(self.choices)))
        return optgroups

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if selected and name != self.other_option_name:
            self.any_selected = True
        return option

    def create_other_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """Creates the 'other' option"""
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option["template_name"] = "utils/snippets/otherradio_option.html"
        return option
