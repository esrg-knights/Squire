import json
import requests

from mailcow_integration.client import MailcowAPIClient

if __name__ == "__main__":
    # Mailcow API cannot handle ipv6. This hack forces usage of ipv4
    requests.packages.urllib3.util.connection.HAS_IPV6 = False

    # client = MailcowAPIClient("beta.kotkt.nl", "squire-test")
    res = client.get_alias(4)
    print(res)

    res = client.get_rspamd_setting_all()
    print(list(res))

    res = client.get_rspamd_setting(3)
    print(res)
