from committees.committeecollective import CommitteeBaseConfig, registry


class FakeConfig(CommitteeBaseConfig):
    url_keyword = 'main'
    name = 'Overview'
    url_name = 'group_general'
    order_value = 10


def get_fake_registry():
    return FakeConfig(registry)
