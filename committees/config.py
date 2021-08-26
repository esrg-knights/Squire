from functools import update_wrapper
from importlib import import_module

from django.apps import apps
from django.http import HttpResponseForbidden
from django.urls import reverse


class CommitteeConfig:
    url_keyword = None
    name = None
    tab_select_keyword = None
    url_name = None
    namespace = None

    def get_urls(self):
        """ Builds a list of urls """
        raise NotImplementedError

    @property
    def urls(self):
        return self.get_urls(), self.namespace, self.namespace

    def get_tab_data(self):
        return {
            'name': self.name,
            'tab_select_keyword': self.tab_select_keyword,
            'url_name': self.url_name,
        }

    @classmethod
    def is_valid_for_group(cls, association_group):
        return True


def get_all_configs(request=None):
    """ Returns a list of all setup configs used by this application"""
    configs = []

    for app in apps.get_app_configs():
        try:
            module = import_module(f'{app.name}.committee_pages.config')
        except ModuleNotFoundError:
            pass
        else:
            for name, cls in module.__dict__.items():
                if isinstance(cls, type):
                    # Get all subclasses of SetupConfig, but not accidental imported copies of SetupConfig
                    if issubclass(cls, CommitteeConfig) and cls != CommitteeConfig:
                        config = cls()
                        if request:
                            if config.check_access(request=request):
                                configs.append(config)
                        else:
                            # There is no request, so no filter. Display all possible configs.
                            configs.append(config)
    return configs
