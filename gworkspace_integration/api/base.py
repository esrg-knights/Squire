import logging
from googleapiclient import discovery
from google.oauth2.service_account import Credentials

from core.api_response import GenericAPIResponse


class WorkspaceAPIResponse(GenericAPIResponse):
    """Abstract base class for Google Workspace API responses"""

    logger = logging.getLogger("gworkspace_api")


class GoogleAPIService:
    """
    Base class for an API service provided by Google. Each of their components
    can be interacted with through their own service. E.g. the DirectoryService
    to manage users and groups, or the GMail service for mailing.
    """

    service_name: str = ""
    version: str = ""
    is_admin = False

    def __init__(self, creds: Credentials, domain: str, members_ou: str, admin_username: str = ""):
        if self.is_admin:
            assert admin_username != ""
            creds = creds.with_subject(admin_username)
        self._domain = domain
        self._members_ou = members_ou
        self._service = discovery.build(self.service_name, self.version, credentials=creds)
