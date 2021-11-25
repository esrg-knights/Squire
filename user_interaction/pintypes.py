from django.conf import settings


class PinVisibility:
    """ TODO """
    PIN_PUBLIC = "PIN_PUBLIC"
    PIN_USERS_ONLY = "PIN_USER"
    PIN_MEMBERS_ONLY = "PIN_MEMBER"


class PinType:
    """ TODO """
    template = "pins/default.html"
    name = "PinType"

    default_pin_title = "Squire Pin"
    default_pin_description = "This pin is lacking a description! If you see this, high-five the person on your left but don't tell them why!"
    default_pin_image = f"{settings.STATIC_URL}images/default_logo.png"
    default_pin_url = None
    default_pin_visibility = PinVisibility.PIN_USERS_ONLY

    def __init__(self, pin_obj):
        self.pin_obj = pin_obj
        self.content_obj = pin_obj.content_object

    @property
    def pin_title(self):
        return self.pin_obj.title or self.default_pin_title

    @property
    def pin_description(self):
        return self.pin_obj.description or self.default_pin_description

    @property
    def pin_image(self):
        return self.pin_obj.image or self.default_pin_image

    @property
    def pin_url(self):
        return self.pin_obj.url or self.default_pin_url


class GenericPin(PinType):
    """ TODO """
    name = "Generic Pin"


class SquireUpdatePin(PinType):
    """ TODO """
    name = "Squire Update"
    default_pin_title = "Squire Update"
    default_pin_visibility = PinVisibility.PIN_PUBLIC


class ActivityMomentPin(PinType):
    """ TODO """
    name = "Activity"
    @property
    def pin_title(self):
        return self.pin_obj.title or self.content_obj.title

    @property
    def pin_description(self):
        return self.pin_obj.description or (self.content_obj.location + self.content_obj.description)

    @property
    def pin_image(self):
        return self.pin_obj.image or self.content_obj.slots_image or self.default_pin_image

    @property
    def pin_url(self):
        return self.pin_obj.url or self.content_obj.get_absolute_url()


class ItemPin(PinType):
    """ TODO """
    name = "New Inventory Item"


PINTYPES = {
    'PIN_GENERIC': GenericPin,
    'PIN_SQUIRE_UPDATE': SquireUpdatePin,
    'PIN_ACTIVITY': ActivityMomentPin,
    'PIN_ITEM': ItemPin,
}
