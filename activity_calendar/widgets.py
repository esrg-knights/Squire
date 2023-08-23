from django.utils.timezone import now
from tempus_dominus.widgets import DateTimePicker


__all__ = ["BootstrapDateTimePickerInput"]


class BootstrapDateTimePickerInput(DateTimePicker):
    def __init__(self, *args, set_min_date_to_now=False, options=None, **kwargs):
        """
        A widget that allows easier front end date time selection, inherited from tempus_dominus
        :param args:
        :param set_min_date_to_now: Boolean determining whether dates can only be picked in the future
        (does not validate in form!)
        :param options: Javascript options as defined here: https://getdatepicker.com/5-4/Options/
        :param kwargs:
        """
        kwargs["options"] = options or {}
        kwargs["options"].update(
            {
                "icons": {
                    "time": "fas fa-clock",
                    "date": "fas fa-calendar",
                    "up": "fas fa-arrow-up",
                    "down": "fas fa-arrow-down",
                    "previous": "fas fa-chevron-left",
                    "next": "fas fa-chevron-right",
                    "today": "fas fa-calendar-check-o",
                    "clear": "fas fa-trash",
                    "close": "fas fa-times",
                },
                "format": "YYYY-MM-DD HH:mm",
            }
        )

        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("input_group", False)

        self.set_min_date_to_now = set_min_date_to_now
        super(BootstrapDateTimePickerInput, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if self.set_min_date_to_now:
            self.js_options["minDate"] = now().date().strftime("%Y-%m-%d 00:00")
        return super(BootstrapDateTimePickerInput, self).render(name, value, attrs=attrs, renderer=renderer)
