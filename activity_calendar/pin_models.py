from django.db.models import DateTimeField, DurationField, ExpressionWrapper

from core.pin_models import PinVisualiserBase


class ActivityMomentPinVisualiser(PinVisualiserBase):
    """ Visualiser for pins with an ActivityMoment attached to them """

    # Database fieldnames
    pin_date_query_fields = ('local_start_date', 'recurrence_id')
    pin_publish_query_fields = ('parent_activity__published_date',)
    pin_expiry_query_fields = ('local_start_date', 'recurrence_id')

    # Attributes
    pin_title_field = "title"
    pin_date_field = "start_date"
    pin_expiry_field = "end_date"

    def get_pin_description(self, pin):
        return self.instance.description.as_raw()

    def get_pin_url(self, pin):
        return self.instance.get_absolute_url()

    def get_pin_image(self, pin):
        if self.instance.parent_activity.slots_image is None:
            return None
        return self.instance.parent_activity.slots_image.image.url

    def get_pin_publish_date(self, pin):
        return self.instance.parent_activity.published_date


class ActivitySlotPinVisualiser(PinVisualiserBase):
    """ Visualiser for pins with an ActivitySlot attached to them """
    # This isn't entirely correct, as activitymoments can have alternative
    #   start/end times. There is no way, however, to fetch that from
    #   the slot object itself. Can be fixed once slots are properly
    #   attached to ActivityMoments instead. See #83

    # Database fieldnames
    pin_date_query_fields = ('recurrence_id',)
    pin_publish_query_fields = ('parent_activity__published_date',)
    pin_expiry_query_fields = ('recurrence_id',)

    # Attributes
    pin_title_field = "title"
    pin_description_field = "description"
    pin_date = "recurrence_id"
    pin_publish_date = "recurrence_id"
    pin_expiry_date = "recurrence_id"

    def get_pin_url(self, pin):
        return self.instance.get_absolute_url()

    def get_pin_image(self, pin):
        if self.instance.parent_activity.slots_image is None:
            return None
        return self.instance.parent_activity.slots_image.image.url

    def get_pin_publish_date(self, pin):
        return self.instance.parent_activity.published_date
