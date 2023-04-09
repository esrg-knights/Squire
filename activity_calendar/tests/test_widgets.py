from django.test import TestCase

from unittest.mock import patch


from activity_calendar.widgets import BootstrapDateTimePickerInput

from . import mock_now


class BootstrapDateTimePickerInputTestCase(TestCase):
    def test_option_defaults(self):
        widget = BootstrapDateTimePickerInput()
        self.assertEqual(widget.js_options["icons"]["time"], "fas fa-clock")
        self.assertEqual(widget.js_options["icons"]["date"], "fas fa-calendar")
        self.assertEqual(widget.js_options["icons"]["up"], "fas fa-arrow-up")
        self.assertEqual(widget.js_options["icons"]["down"], "fas fa-arrow-down")
        self.assertEqual(widget.js_options["icons"]["previous"], "fas fa-chevron-left")
        self.assertEqual(widget.js_options["icons"]["next"], "fas fa-chevron-right")
        self.assertEqual(widget.js_options["icons"]["today"], "fas fa-calendar-check-o")
        self.assertEqual(widget.js_options["icons"]["clear"], "fas fa-trash")
        self.assertEqual(widget.js_options["icons"]["close"], "fas fa-times")

        self.assertEqual(widget.js_options["format"], "YYYY-MM-DD HH:mm")

    def test_attr_defaults(self):
        widget = BootstrapDateTimePickerInput()
        # Defaults to True in tempus_dominus, but conflicts with our render_field templatetag so should default False
        self.assertEqual(widget.attrs["input_group"], False)

    def test_render_no_min_date(self):
        widget = BootstrapDateTimePickerInput(attrs={"id": "test_widget"})
        widget.render("test_name", None)
        self.assertEqual(widget.js_options.get("minDate", None), None)

    @patch("activity_calendar.widgets.now", side_effect=mock_now())
    def test_render_with_min_date(self, mock):
        widget = BootstrapDateTimePickerInput(attrs={"id": "test_widget"}, set_min_date_to_now=True)
        widget.render("test_name", None)
        self.assertEqual(widget.js_options.get("minDate", None), "2020-08-11 00:00")
