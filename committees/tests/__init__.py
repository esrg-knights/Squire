from committees.committeecollective import CommitteeBaseConfig, registry
from committees.options import SettingsOptionBase


class FakeConfig(CommitteeBaseConfig):
    url_keyword = "main"
    name = "Overview"
    url_name = "group_general"
    order_value = 10


def get_fake_config():
    return FakeConfig(registry)


class FakeOption(SettingsOptionBase):
    name = "Fake Options"
    option_template_name = "committees/test/test_setting_option_layout.html"


def get_fake_option():
    return FakeOption()
