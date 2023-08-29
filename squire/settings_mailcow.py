# Copy all settings from the base file
from .settings import *

####################################################################
# Connection configurations to external services
####################################################################
# Why is this a separate file?
#   When running the server in production (or development), connection options
#       are likely set up. Yet, we do not want tests to accidentally connect
#       to the server using this connection. The existence of a configuration
#       file is therefore not enough to determine whether to possibly connect.
#   Environment variables does not suffice, as those are shared by
#       the test runner and runserver-command.
#   Overriding the settings for all test classes is infeasible, and will not
#       prevent connections for other management commands (e.g. migrations).
#
#   Hence, to guarantee that a connection is not made in unwanted
#       situations (e.g. tests), this settings file needs to be explicitly
#       passed to a management command.
#   Usage: `<management-command> --settings squire.settings_mailcow`
####################################################################

####################################################################
# Mailcow API
#   If MAILCOW_HOST is None, no API connection is established
try:
    with open(os.path.join(BASE_DIR, "squire", "mailcowconfig.json"), "r") as mailcow_config_fp:
        _mailcow_config = json.load(mailcow_config_fp)

        MAILCOW_HOST = _mailcow_config["host"]
        MAILCOW_API_KEY = _mailcow_config["api_key"]

        MEMBER_ALIASES = _mailcow_config["member_aliases"]
        COMMITTEE_CONFIGS = _mailcow_config["committee_aliases"]
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    # Something went wrong in parsing the config file
    MAILCOW_HOST = None
    MAILCOW_API_KEY = None
    MEMBER_ALIASES = {}
    COMMITTEE_CONFIGS = {"archive_addresses": [], "global_addresses": [], "global_archive_addresses": []}
