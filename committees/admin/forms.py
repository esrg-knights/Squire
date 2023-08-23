from django.contrib.auth.models import Permission
from django.forms import Form
from django.forms.fields import BooleanField
from django.forms.widgets import Input

from committees.committeecollective import registry, CommitteeBaseConfig
from .models import AssociationGroupPanelControl


class ConfigTabSelectWidget(Input):
    template_name = "committees/admin/widgets/config_access_widget.html"

    def __init__(self, attrs=None, config: CommitteeBaseConfig = None):
        super(ConfigTabSelectWidget, self).__init__(attrs=attrs)
        self.config = config

    def get_context(self, name, value, attrs):
        attrs["config"] = self.config
        attrs["default_enabled"] = self.config.group_requires_permission is None
        if value:
            attrs["checked"] = True
        return super().get_context(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, False)
        # Translate true and false strings to boolean values.
        values = {"true": True, "false": False}
        if isinstance(value, str):
            value = values.get(value.lower(), value)
        return bool(value)

    def value_omitted_from_data(self, data, files, name):
        # HTML checkboxes don't appear in POST data if not checked, so it's
        # never known if the value is actually omitted.
        return False


class AssociationGroupsTabAccessForm(Form):
    """Form that allows changing of tab access for the given AssociationGroupPanelControl instance"""

    def __init__(self, *args, instance: AssociationGroupPanelControl = None, **kwargs):
        super(AssociationGroupsTabAccessForm, self).__init__(*args, **kwargs)
        self.instance = instance
        for config in registry.configs:
            self._build_config_field(config)
        self.fields = self.base_fields
        # The form requires all fields in fields, but the admin requires it all in base_fields, co copy the list

    def _build_config_field(self, config: CommitteeBaseConfig):
        if config.is_default_for_group(self.instance):
            initial = None
        else:
            initial = config.check_group_access(self.instance)
        self.base_fields[config.name] = BooleanField(
            initial=initial,
            widget=ConfigTabSelectWidget(config=config),
            required=False,
        )

    def save(self, commit=None):
        for config in registry.configs:
            if config.is_default_for_group(self.instance):
                continue
            if self.base_fields[config.name].initial == self.cleaned_data[config.name]:
                # Nothing changed, save nothing
                continue
            if self.cleaned_data[config.name]:
                config.enable_access(self.instance)
            else:
                config.disable_access(self.instance)

        return self.instance

    def save_m2m(self):
        # Required to be used in the admin
        pass
