import logging
from core.api_response import GenericAPIResponse


class WorkspaceAPIResponse(GenericAPIResponse):
    """Abstract base class for Google Workspace API responses"""

    ignore_extra = True

    logger = logging.getLogger("gworkspace_api")
