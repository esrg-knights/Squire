from django.conf import settings


class DefaultSite:
    """
        A class that shares the primary interface of Site (i.e., it has ``domain``
        and ``name`` attributes) but it retrieves the data from the settings config
        The save() and delete() methods raise NotImplementedError.
    """
    @property
    def domain(self):
        return settings.SITE_DOMAIN

    @property
    def name(self):
        return settings.SITE_NAME

    def save(self, force_insert=False, force_update=False):
        raise NotImplementedError("DefaultSite cannot be saved.")

    def delete(self):
        raise NotImplementedError("DefaultSite cannot be deleted.")
