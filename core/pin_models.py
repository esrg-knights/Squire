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

    # Fieldnames to copy pin information from
    pin_title_field = None
    pin_description_field = None
    pin_url_field = None
    pin_image_field = None
    pin_publish_field = None
    pin_expiry_field = None
    pin_date_field = None

    # Add a GenericRelation, which handles auto-deleting a pin if the related
    #   object no longer exists
    pins = GenericRelation("core.Pin", related_query_name="%(app_label)s_%(class)s_pinnable")

    @classmethod
    def get_pin_title_query(cls):
        return F(cls.pin_title_field)

    @classmethod
    def get_pin_description_query(cls):
        return F(cls.pin_description_field)

    @classmethod
    def get_pin_url_query(cls):
        return F(cls.pin_url_field)

    @classmethod
    def get_pin_image_query(cls):
        return F(cls.pin_image_field)

    @classmethod
    def get_pin_publish_query(cls):
        return F(cls.pin_publish_field)

    @classmethod
    def get_pin_expiry_query(cls):
        return F(cls.pin_expiry_field)

    @classmethod
    def get_pin_date_query(cls):
        return F(cls.pin_date_field)

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
    def for_user(self, user, limit_to_highlights=False, queryset=None):
        assert user is not None
        now = timezone.now()

        pins = Pin.objects.filter(content_type_id__isnull=True).annotate(
            pin_date=F('local_pin_date'),
            # publish_date=F('local_publish_date'),
            # expiry_date=F('local_expiry_date'),
        )

        for content_type in ContentType.objects.all():
            model_class: PinnableModelMixin = content_type.model_class()
            if model_class is not None and issubclass(model_class, PinnableModelMixin):
                model_class_pins = Pin.objects.filter(content_type_id=content_type.id).prefetch_related('content_object').annotate(
                    pin_date=Coalesce(F('local_pin_date'), model_class.get_pin_date_query()),
                    # publish_date=F('local_publish_date'),
                    # expiry_date=F('local_expiry_date'),
                )

                pins = pins.union(model_class_pins)

        # Method 1
        #
        # pins = Pin.objects.filter(content_type_id__isnull=True).annotate(
        #     pin_title=F('local_title'),
        #     # pinnable_description=Coalesce(F('pins__local_description'), model_class.get_pin_description_query()),
        #     pin_pin_date=F('local_pin_date'),
        #     pin_publish_date=F('local_publish_date'),
        #     pin_expiry_date=F('local_expiry_date'),
        # ).values('pin_title', 'pin_pin_date', 'pin_publish_date', 'pin_expiry_date')

        # for content_type in ContentType.objects.all():
        #     model_class: PinnableModelMixin = content_type.model_class()
        #     if model_class is not None and issubclass(model_class, PinnableModelMixin):

        #         # TODO: limit selection;
        #         # TODO: select_related
        #         pinnables = model_class.objects.filter(pins__isnull=False).annotate(
        #             pin_creation_date=models.F('pins__creation_date'),
        #             pin_title=Coalesce(F('pins__local_title'), model_class.get_pin_title_query()),
        #             # pinnable_description=Coalesce(F('pins__local_description'), model_class.get_pin_description_query()),
        #             pin_pin_date=Coalesce(F('pins__local_pin_date'), model_class.get_pin_date_query()),
        #             pin_publish_date=Coalesce(F('pins__local_publish_date'), model_class.get_pin_publish_query()),
        #             pin_expiry_date=model_class.get_pin_expiry_query(),
        #         ).values('pin_title', 'pin_pin_date', 'pin_publish_date', 'pin_expiry_date')


        #         print(pinnables.query)
        #         print(pinnables)
        #         pins = pins.union(pinnables)

        #         # django.core.exceptions.FieldError: Field 'content_object' does not generate an automatic
        #         #   reverse relation and therefore cannot be used for reverse querying. If it is a
        #         #   GenericForeignKey, consider adding a GenericRelation.
        #         #
        #         # Pin.objects.filter(content_type_id=content_type.id) \
        #         #     .prefetch_related('content_object') \
        #         #     .annotate(pin_title=Coalesce(models.F('local_title'), models.F('content_object__title')))
        #         #
        #         # Pin.objects.filter(content_type_id=22) \
        #         #     .prefetch_related('content_object') \
        #         #     .annotate(pin_title=Coalesce(models.F('local_title'), models.F('content_object__title')))

        #         # TODO: limit selection;
        #         # TODO: select_related
        #         # from activity_calendar.models import ActivityMoment
        #         # x = ActivityMoment.objects.filter(pins__isnull=False).select_related('parent_activity').annotate(
        #         #     pin_title=Coalesce(models.F('pins__local_title'), models.F('local_title')),
        #         #     pin_creation_date=models.F('pins__creation_date'),
        #         #     pin_publish_date=Coalesce(models.F('pins__local_publish_date'), models.F('parent_activity__published_date')),
        #         # ).order_by('-id')

        print(pins)

        print("----")
        for pin in pins.order_by('pin_date'):
            print(f"{pin.local_title}/{pin.content_object} - {pin.pin_date}")
            # print(pin.pin_title)
            # print(pin.pin_pin_date)
            # print(pin.pin_expiry_date)
            # print(pin.content_object)

        print(f"There are {len(pins)} pins total")
        print(pins.query)

        return pins
                # Annotate with attributes to copy to pin, Perform a Union



    def for_user_____OLD(self, user, limit_to_highlights=False, queryset=None):
        """ Return a queryset consisting of Pins visible to the given user. """
        assert user is not None
        now = timezone.now()

        if queryset is None:
            queryset = Pin.objects.all()

        # Is the user unable to view not-yet-published pins?
        if not user.has_perm('core.can_view_future_pins'):
            # Must not have a future publish date
            queryset = queryset.exclude(local_publish_date__gt=now)

            # Must not be unpublished
            queryset = queryset.exclude(local_publish_date__isnull=True, object_id__isnull=True)

        # Is the user unable to view expired pins?
        if not user.has_perm('core.can_view_expired_pins'):
            # Must not have passed its expiration date
            queryset = queryset.exclude(local_expiry_date__lte=now)

        # Is the user unable to view member-only pins?
        if not user.has_perm('core.can_view_members_only_pins'):
            queryset = queryset.exclude(is_members_only=True)

        # Handle highlights
        if limit_to_highlights:
            queryset = queryset.exclude(pin_sort_date__gt=True)

        # Handle auto-copying from content_object that inherits from PinnableMixin (local values have priority)
        #   This'll create a separate query for each Pinnable model (just like prefetch_related), but in
        #   return we don't need to perform any joins over generic foreign keys.
        content_type_queries = models.Q()
        for content_type in ContentType.objects.all():
            if not issubclass(content_type, PinnableModelMixin):
                model_class: PinnableModelMixin = content_type.model_class()
                ct_query = models.Q()

                if not user.has_perm('core.can_view_future_pins'):
                    # Filter only published pinnables
                    ct_query &= model_class.get_pin_publish_date_query(now)

                if not user.has_perm('core.can_view_expired_pins'):
                    # Filter only non-expired pinnables
                    ct_query &= model_class.get_pin_expiry_date_query(now)

                valid_objs = content_type.model_class().objects.filter(ct_query).values_list('pk', flat=True)
                content_type_queries |= models.Q(content_type_id=content_type.id, object_id__in=valid_objs)
        queryset = queryset.filter(content_type_queries | models.Q(content_type_id__isnull=True))

        return queryset


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

    # @property
    # def title(self):
    #     if not self.local_title and self.content_object is not None:
    #         # No local title, so fetch related model title
    #         return self.content_object.get_pin_title(self)
    #     return self.local_title

    # @property
    # def description(self):
    #     if not self.local_description and self.content_object is not None:
    #         return self.content_object.get_pin_description(self)
    #     return self.local_description

    # @property
    # def url(self):
    #     if not self.local_url and self.content_object is not None:
    #         return self.content_object.get_pin_url(self)
    #     return self.local_url or None

    # @property
    # def image(self):
    #     if self.local_image is not None:
    #         # local override
    #         return self.local_image.image.url

    #     if self.content_object is not None:
    #         # image provided by content object
    #         img = self.content_object.get_pin_image(self)
    #         if img is not None:
    #             return img
    #     # no image whatsoever
    #     return f"{settings.STATIC_URL}images/default_logo.png"

    # @property
    # def has_image(self):
    #     return self.local_image is not None or \
    #         (self.content_object is not None and self.content_object.get_pin_image(self) is not None)

    # @property
    # def publish_date(self):
    #     if self.local_publish_date is None and self.content_object is not None:
    #         return self.content_object.get_pin_publish_date(self)
    #     return self.local_publish_date

    # @property
    # def expiry_date(self):
    #     if self.local_expiry_date is None and self.content_object is not None:
    #         return self.content_object.get_pin_expiry_date(self)
    #     return self.local_expiry_date

    # def is_published(self):
    #     """ Whether this pin is published """
    #     publish_date = self.publish_date
    #     return publish_date is not None and publish_date <= timezone.now()

    # def is_expired(self):
    #     """ Whether this pin has expired """
    #     expiry_date = self.expiry_date
    #     return expiry_date is not None and expiry_date <= timezone.now()

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
        if self.content_object is not None:
            return self.content_object.pin_template_short or self.default_pin_template_short
        return self.default_pin_template_short

    def get_pin_template_long(self):
        """ Gets the large template used by this pin """
        if self.content_object is not None:
            return self.content_object.pin_template_long or self.default_pin_template_long
        return self.default_pin_template_long

    def __str__(self):
        return f"Pin {self.id} - {self.local_title} ({self.content_object})"
