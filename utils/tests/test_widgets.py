from django.test import TestCase

from utils.widgets import OtherRadioSelect


class OtherWidgetTestCase(TestCase):
    """Tests for the OtherRadioSelect widget"""

    def setUp(self) -> None:
        self.widget = OtherRadioSelect(
            choices=[("a_value", "a label"), ("b_value", "b label"), ("c_value", "c label")]
        )
        return super().setUp()

    def test_radiolist_class(self):
        """Tests if the radiolist class is added correctly"""
        # No override class passed
        self.assertEqual(self.widget.attrs.get("class", None), "radiolist")
        # Override class passed
        widget = OtherRadioSelect(
            choices=[("a_value", "a label"), ("b_value", "b label"), ("c_value", "c label")], attrs={"class": "foo"}
        )
        self.assertEqual(widget.attrs.get("class", None), "foo")

    def test_get_context_other(self):
        """Tests if the free-text widget's context is also passed"""
        # Value is one of the preset options
        context = self.widget.get_context("test_field", "b_value", {"class": "foo"})
        self.assertIsNotNone(context.get("other_widget", None))
        other_widget = context["other_widget"]
        self.assertEqual(other_widget["name"], OtherRadioSelect.other_field_name % "test_field")
        # Value is one of the preset options; widget should be empty and disabled
        self.assertIsNone(other_widget["value"])
        self.assertTrue(other_widget["attrs"]["disabled"])
        # Class is overridden
        self.assertEqual(other_widget["attrs"]["class"], "foo")

        # Value is not a preset option
        context = self.widget.get_context("test_field", "free text value", None)
        other_widget = context["other_widget"]
        self.assertEqual(other_widget["value"], "free text value")
        self.assertFalse(other_widget["attrs"]["disabled"])
        # Class is inherited from base radioWidget
        self.assertEqual(other_widget["attrs"]["class"], "radiolist")

    def test_get_value(self):
        """Tests if the value entered in the other option can be retrieved"""
        # Mimic some POST data (preset option)
        val = self.widget.value_from_datadict({"test_field": "b_value"}, {}, "test_field")
        self.assertEqual(val, "b_value")

        # Other option
        val = self.widget.value_from_datadict(
            {
                "test_field": OtherRadioSelect.other_option_name,
                OtherRadioSelect.other_field_name % "test_field": "not a preset value!",
            },
            {},
            "test_field",
        )
        self.assertEqual(val, "not a preset value!")
        self.assertNotEqual(val, OtherRadioSelect.other_option_name)

    def test_optgroups(self):
        """Tests if an 'other' option is properly created"""
        optgroups = self.widget.optgroups("test_field", ["b_value"], None)
        # An additional optgroup should be created
        self.assertEqual(len(optgroups), 4)
        optgroup_name, other_option, index = optgroups[-1]
        self.assertIsNone(optgroup_name)
        self.assertEqual(index, 3)
        other_option = other_option[0]
        self.assertEqual(other_option["name"], "test_field")
        self.assertEqual(other_option["value"], OtherRadioSelect.other_option_name)
        self.assertEqual(other_option["label"], "Other:")
        # Not selected, because a preset was selected
        self.assertFalse(other_option["selected"])
        self.assertEqual(other_option["index"], "3")
        self.assertEqual(other_option["template_name"], "utils/snippets/otherradio_option.html")

        optgroups = self.widget.optgroups("test_field", ["free text option"], None)
        _, other_option, _ = optgroups[-1]
        other_option = other_option[0]
        # Selected, because no preset was selected
        self.assertTrue(other_option["selected"])
