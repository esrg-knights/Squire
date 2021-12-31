from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.models import PresetImage

def now_rounded():
    """ Returns timezone.now rounded down to the nearest hour """
    return timezone.now().replace(minute=0, second=0)

def now_one_week_later():
    """ Returns the datetime a week from timezone.now """
    return now_rounded() + timezone.timedelta(days=7)

def now_one_year_later():
    """ Returns the datetime a year from timezone.now """
    return now_rounded() + timezone.timedelta(days=365)

def valid_pinnable_models():
    """ Returns a dictionary consisting of ContentTypes whose corresponding model instances can be pinned. """
    valid_ids = []
    for content_type in ContentType.objects.all():
        model_class = content_type.model_class()
        if model_class is not None and issubclass(model_class, PinnableModelMixin):
            valid_ids.append(content_type.id)
    return {'id__in': valid_ids}


class PinnableModelMixin(models.Model):
    """
        Mixin that marks the model inheriting this class as "Pinnable". This
        allows that model to be linked to a Pin, allowing the pin to automatically
        copy values from the inheriting model.

        The instance variables pin_foo_field (for each field 'foo') determine
        where to copy information from. If None, this information will not be copied.

        The methods get_pin_foo(self, pin) (for each field 'foo') can be overridden to
        directly determine what should be returned for the pin's 'foo' attribute. This
        is a more flexible alternative to providing just a field to copy from.
        For instance, it can be used to combine two model fields and return that as the
        pin's description.

        The field 'pins' is added as a GenericRelation in order to auto-delete pins that
        are linked to the inherited object.
    """
    class Meta:
        # We don't actually want this class in the database, but
        #   since we're adding a field (even if it's only a lookup)
        #   we still need to inherit from models.Model
        abstract = True

    pin_template_short = None
    pin_template_long = None
    pin_view_permissions = () # Additional permissions needed to view this pin

    # Iterables of field names to copy information from, taking the first non-null field value.
    #   TODO
    pin_date_query_fields = None
    pin_publish_query_fields = None
    pin_expiry_query_fields = None

    # Fieldnames to copy pin information from
    pin_title_field = None
    pin_description_field = None
    pin_url_field = None
    pin_image_field = None
    pin_date_field = None
    pin_publish_field = None
    pin_expiry_field = None

    def get_pin_title(self, pin):
        """ Title for pins that have this object attached to them """
        if self.pin_title_field:
            return getattr(self, self.pin_title_field, None)

    def get_pin_description(self, pin):
        """ Description for pins that have this object attached to them """
        if self.pin_description_field:
            return getattr(self, self.pin_description_field, None)

    def get_pin_url(self, pin):
        """ Title for pins that have this object attached to them """
        if self.pin_url_field:
            return getattr(self, self.pin_url_field, None)

    def get_pin_image(self, pin):
        """ Image for pins that have this object attached to them """
        if self.pin_image_field:
            image_field = getattr(self, self.pin_image_field, None)
            if image_field:
                return image_field.url
        return None

    def get_pin_date(self, pin):
        if self.pin_date_field:
            return getattr(self, self.pin_date_field, None)

    def get_pin_publish_date(self, pin):
        """ Publish date for pins that have this object attached to them """
        if self.pin_publish_field:
            return getattr(self, self.pin_publish_field, None)

    def get_pin_expiry_date(self, pin):
        """ Expiry Date for pins that have this object attached to them """
        if self.pin_expiry_field:
            return getattr(self, self.pin_expiry_field, None)



    # Add a GenericRelation, which handles auto-deleting a pin if the related
    #   object no longer exists. Also allows reverse relations.
    pins = GenericRelation("core.Pin", related_query_name="%(app_label)s_%(class)s_pinnable")

    def clean_pin(self, pin):
        """
            Allow pins that have this object attached to fail validation
            during the pin's clean method if this method raises a ValidationError.

            For instance, this can be used for models with their own publish date
            to prevent them from being pinned while they are still unpublished.
        """
        pass


class PinManager(models.Manager):
    """
        Model Manager that also provides a method to list pins
        that are visible to a given user.
    """

    def _get_pin_field_cases(self, model_class, pin_fields):
        whens = []
        for field in pin_fields:
            if isinstance(field, str):
                whens.append(F(f"{model_class.pins.rel.related_name}__{field}"))
                # # Just an existing field name; easy
            else:
                # Method was passed
                method = field[0]
                d = []
                for actual_field in field[1]:
                    val = F(f"{model_class.pins.rel.related_name}__{actual_field}")
                    d.append(val)
                whens.append(
                    method(*d)
                )
        return whens

    def _get_pin_field_query(self, model_class, local_field, pin_fields):
        # Coalesce takes the first non-NULL value.
        return Coalesce(
            local_field,
            *self._get_pin_field_cases(model_class, pin_fields),
        )

    def for_user(self, user, limit_to_highlights=False, queryset=None):
        assert user is not None
        now = timezone.now()

        # Get all pins without a content_object and fetch their information
        #   Annotate certain fields to a unified name
        pins = Pin.objects.filter(content_type_id__isnull=True).annotate(
            pin_query_date=F('local_pin_date'),
            publish_query_date=F('local_publish_date'),
            expiry_query_date=F('local_expiry_date'),
        )

        # For each pinnable object, fetch their info
        for content_type in ContentType.objects.all():
            model_class: PinnableModelMixin = content_type.model_class()
            # Must be a pinnable model
            if model_class is not None and issubclass(model_class, PinnableModelMixin):
                # Fetch all pins related to this model
                model_class_pins = Pin.objects.filter(content_type_id=content_type.id).annotate(
                    pin_query_date=self._get_pin_field_query(model_class, 'local_pin_date', model_class.pin_date_query_fields),
                    publish_query_date=self._get_pin_field_query(model_class, 'local_publish_date', model_class.pin_publish_query_fields),
                    expiry_query_date=self._get_pin_field_query(model_class, 'local_expiry_date', model_class.pin_expiry_query_fields),
                )

                # Obtain the UNION of the pins for this model class and those that were fetched earlier
                pins = pins.union(model_class_pins)

        # Prefetch related content objects to reduce further queries
        # Newest pins appear first
        return pins.prefetch_related('content_object').order_by('-pin_query_date')


class Pin(models.Model):
    """
    A pin is a small notification on the homepage. If linked to a specific model instance that inherits
    PinnableMixin, it copies over the attributes for the title, description, etc. based on fields (or
    methods) of that model instance. This auto-copying can be overridden if local values for the pin are
    provided instead.
    """
    objects = PinManager()
    default_pin_template_short = "core/pins/default.html" # The default template used to render a pin
    default_pin_template_long = "core/pins/default_long.html"

    class Meta:
        permissions = [
            ('can_view_members_only_pins',  "[F] Can view pins that are marked as 'members only'."),
            ('can_view_expired_pins',       "[F] Can view pins that have expired."),
            ('can_view_future_pins',        "[F] Can view pins with a publish date in the future."),
        ]

    # Date and creator of the pin
    creation_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    # A way to categorise pins
    category = models.CharField(max_length=127)
    highlight_duration = models.DurationField(blank=True, null=True, help_text="How long this pin will be highlighted on the homepage. It will still be accessible until it expires. Leave empty to highlight it until it expires.")

    # Standard Information
    local_title = models.CharField(max_length=255, blank=True, null=True)
    local_description = models.TextField(blank=True, null=True)
    local_url = models.URLField(blank=True, null=True)
    local_image = models.ForeignKey(PresetImage, on_delete=models.SET_NULL, blank=True, null=True)

    # Visibility Requirements
    local_pin_date = models.DateTimeField(default=now_rounded, null=True, blank=True, help_text="Pins are sorted based on this value.")
    local_publish_date = models.DateTimeField(default=now_rounded, null=True, blank=True, help_text="The date at which this pin becomes available. Can be left empty to never become available.")
    local_expiry_date = models.DateTimeField(default=now_one_year_later, null=True, blank=True, help_text="The date at which this pin is no longer available. Can be left empty to not expire.")
    is_members_only = models.BooleanField(default=True, help_text="'Members-only' pins can only be viewed by those with the permission to do so.")

    # Related Model instance (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, limit_choices_to=valid_pinnable_models)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    @property
    def title(self):
        if not self.local_title and self.content_object is not None:
            # No local title, so fetch related model title
            return self.content_object.get_pin_title(self)
        return self.local_title

    @property
    def description(self):
        if not self.local_description and self.content_object is not None:
            return self.content_object.get_pin_description(self)
        return self.local_description

    @property
    def url(self):
        if not self.local_url and self.content_object is not None:
            return self.content_object.get_pin_url(self)
        return self.local_url

    @property
    def image(self):
        return self.get_image()

    def get_image(self, default=f"{settings.STATIC_URL}images/default_logo.png"):
        if self.local_image is not None:
            # local override
            return self.local_image.image.url

        if self.content_object is not None:
            # image provided by content object
            img = self.content_object.get_pin_image(self)
            if img is not None:
                return img
        return default

    @property
    def has_image(self):
        return self.get_image(default=None) is not None

    @property
    def pin_date(self):
        if self.local_pin_date is None and self.content_object is not None:
            return self.content_object.get_pin_date(self)
        return self.local_pin_date

    @property
    def publish_date(self):
        if self.local_publish_date is None and self.content_object is not None:
            return self.content_object.get_pin_publish_date(self)
        return self.local_publish_date

    @property
    def expiry_date(self):
        if self.local_expiry_date is None and self.content_object is not None:
            return self.content_object.get_pin_expiry_date(self)
        return self.local_expiry_date

    def is_published(self):
        """ Whether this pin is published """
        publish_date = self.publish_date
        return publish_date is not None and publish_date <= timezone.now()

    def is_expired(self):
        """ Whether this pin has expired """
        expiry_date = self.expiry_date
        return expiry_date is not None and expiry_date <= timezone.now()

    # def can_view_pin(self, user):
    #     """ Whether the given user can see this pin """
    #     required_perms = []
    #     if not self.is_published and self.publish_date is not None:
    #         # Pin will be published in the future
    #         required_perms.append('core.can_view_future_pins')
    #     elif self.is_expired:
    #         # Pin has expired
    #         required_perms.append('core.can_view_expired_pins')

    #     if self.is_members_only:
    #         # Pin is marked as 'members-only'
    #         required_perms.append('core.can_view_members_only_pins')

    #     if self.content_object is not None:
    #         required_perms = required_perms + list(self.content_object.pin_view_permissions)

    #     return user.has_perms(required_perms)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        # Make exlude a list to prevent complex if statements
        exclude = exclude or []

        if 'content_type' not in exclude and 'object_id' not in exclude:
            if self.content_type is not None and self.content_object is None:
                raise ValidationError({
                    'content_type': ValidationError("The connected instance does not exist", code='instance_nonexistent')
                })

    def clean(self):
        super().clean()
        if self.publish_date is not None and self.expiry_date is not None:
            if self.publish_date > self.expiry_date:
                raise ValidationError({
                    'publish_date': ValidationError("The pin cannot be published after it expires", code='invalid_duration')
                })

        if self.content_object is not None:
            # Ensure that local data entered in this pin is valid when
            #   other data is copied form the related object
            self.content_object.clean_pin(self)

    def get_pin_template_short(self):
        """ Gets the short template used by this pin"""
        # if self.content_object is not None:
        #     return self.content_object.pin_template_short or self.default_pin_template_short
        return self.default_pin_template_short

    def get_pin_template_long(self):
        """ Gets the large template used by this pin """
        # if self.content_object is not None:
        #     return self.content_object.pin_template_long or self.default_pin_template_long
        return self.default_pin_template_long

    def __str__(self):
        return f"Pin {self.id} - {self.local_title} ({self.content_object})"
