class ClientNotImplemented(Exception):
    def __str__(self):
        return (
            "Client is not active, as not all neccessary attributes are set correctly. Make sure that "
            "the following settings are defined in your settings or local_settings file: "
            "NEXTCLOUD_HOST, NEXTCLOUD_USERNAME, and NEXTCLOUD_PASSWORD"
        )
