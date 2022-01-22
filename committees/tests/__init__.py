from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse


from committees.models import AssociationGroup


class AssocationGroupTestingMixin:
    """ Mixin for TestCase that prepares the testcase for the committee_pages environment """
    association_group_id = None
    association_group = None
    url_name = None

    def setUp(self):
        super(AssocationGroupTestingMixin, self).setUp()
        if self.association_group_id is None:
            raise ImproperlyConfigured(f"'association_group_id' was not defined on {self.__class__.__name__}")
        self.association_group = AssociationGroup.objects.get(id=self.association_group_id)

    def get_base_url(self, **url_kwargs):
        if self.url_name is None:
            raise ImproperlyConfigured(f"'url_name' was not defined on {self.__class__.__name__}")
        return reverse('committees:'+self.url_name, kwargs=self.get_url_kwargs(**url_kwargs))

    def get_url_kwargs(self, **kwargs):
        url_kwargs = {
            'group_id': self.association_group_id,
        }
        url_kwargs.update(kwargs)
        return url_kwargs
