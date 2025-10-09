class SquireGoogleWorkspaceManager:
    """
    All interactions Squire makes with the Google Workspace API are handled through this class.
    It is responsible for adding members' emails to a group of member aliases (depending
    on their stored preferences), and adding members' emails to the aliases of committees
    they are in.
    """
