import json
import requests

from mailcow_integration.api.client import MailcowAPIClient

if __name__ == "__main__":
    # Mailcow API cannot handle ipv6. This hack forces usage of ipv4
    requests.packages.urllib3.util.connection.HAS_IPV6 = False

    # NOTE: The Mailcow API uses an IP whitelist. Make sure to add your local IP to this list in the admin panel.
    # client = MailcowAPIClient("beta.kotkt.nl", "<API-key>")
    res = client.get_alias(4)
    print(res)

    res = client.get_rspamd_setting_all()
    print(list(res))

    res = client.get_rspamd_setting(3)
    print(res)

    res.desc = "test (should not be used) [Managed by Squire]"
    client.update_rspamd_setting(res)
