from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import PresetImage
from membership_file.util import get_member_from_user
from user_interaction.pintypes import MEMBERS_ONLY_PINTYPES, PUBLIC_PINTYPES, GenericPin, PINTYPES, PinVisibility

def now_rounded():
    """ Returns timezone.now rounded down to the nearest hour """
    return timezone.now().replace(minute=0, second=0)

def now_one_week_later():
    """ Returns the datetime a week from timezone.now """
    return now_rounded() + timezone.timedelta(days=7)

def valid_pinnable_models():
    """ Returns a dictionary consisting of ContentTypes whose corresponding model instances can be pinned. """
    valid_ids = []
    for content_type in ContentType.objects.all():
        if isinstance(content_type.model_class(), PinnableMixin):
            valid_ids.append(content_type.id)
    return {'id__in': valid_ids}

# def validate_is_pinnable(contenttype: ContentType):
#     """ Validates that a given ContentType inherits from PinnableMixin """
#     if contenttype is None:
#         return
#     if not isinstance(contenttype.model_class(), PinnableMixin):
#         raise ValidationError(f"{contenttype.model_class()._meta.verbose_name_plural} are not pinnable.")

class PinnableMixin:
    """ TODO """
    pin_template = "user_interaction/pins/default.html"
    pin_view_permissions = () # Additional permissions needed to view this pin

    # Fieldnames to copy pin information from
    pin_title_field = None
    pin_description_field = None
    pin_url_field = None
    pin_image_field = None
    pin_publish_field = None
    pin_expiry_field = None

    # TODO: GenericRelation

    def get_pin_title(self):
        """ Title for pins that have this object attached to them """
        return getattr(self, self.pin_title_field, None)

    def get_pin_description(self):
        """ Description for pins that have this object attached to them """
        return getattr(self, self.pin_description_field, None)

    def get_pin_url(self):
        """ Title for pins that have this object attached to them """
        return getattr(self, self.pin_url_field, None)

    def get_pin_image(self):
        """ Image for pins that have this object attached to them """
        return getattr(self, self.pin_image_field, None)

    def get_pin_publish_date(self):
        """ Publish date for pins that have this object attached to them """
        return getattr(self, self.pin_publish_field, None)

    def get_pin_expiry_date(self):
        """ Expiry Date for pins that have this object attached to them """
        return getattr(self, self.pin_expiry_field, None)

class PinManager(models.Manager):
    def for_user(self, user):
        pass

class Pin(models.Model):
    """
    A pin is a small notification on the homepage. If linked to a specific model instance that inherits
    the PinnableMixin, copies over the attributes for the title, description, etc. based on fields (or
    methods) of that model instance unless a local value overrides it.
    """
    objects = PinManager()
    class Meta:
        ordering = ['-local_publish_date']

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

    # Standard Information
    local_title = models.CharField(max_length=255, blank=True)
    local_description = models.TextField(blank=True)
    local_url = models.URLField(blank=True)
    local_image = models.ForeignKey(PresetImage, on_delete=models.SET_NULL, blank=True, null=True)

    # Visibility Requirements
    local_publish_date = models.DateTimeField(default=now_rounded, null=True, blank=True, help_text="The date at which this pin becomes available. Can be left empty to never become available.")
    local_expiry_date = models.DateTimeField(default=now_one_week_later, null=True, blank=True, help_text="The date at which this pin is no longer available. Can be left empty to not expire.")
    is_members_only = models.BooleanField(default=True, help_text="'Members-only' pins can only be viewed by those with the permission to do so.")

    # Related Model instance (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, limit_choices_to=valid_pinnable_models)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    def is_published(self):
        """ Whether this pin is published """
        return self.publish_date is not None and self.publish_date <= timezone.now()

    def is_expired(self):
        """ Whether this pin has expired """
        return self.expiry_date is not None and self.expiry_date <= timezone.now()

    def can_view_pin(self, user):
        """ Whether the given user can see this pin """
        required_perms = []
        if not self.is_published and self.publish_date is not None:
            # Pin will be published in the future
            required_perms.append('user_interaction.can_view_future_pins')
        elif self.is_expired:
            # Pin has expired
            required_perms.append('user_interaction.can_view_expired_pins')

        if self.is_members_only:
            # Pin is marked as 'members-only'
            required_perms.append('user_interaction.can_view_members_only_pins')

        if self.content_object is not None:
            required_perms = required_perms + self.content_object.pin_view_permissions

        return user.has_perms(required_perms)


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
        if self.publish_date is not None and self.expiry_date is not None:
            if self.publish_date > self.expiry_date:
                raise ValidationError({
                    'publish_date': ValidationError("The pin cannot be published after it expires", code='invalid_duration')
                })

    def __str__(self):
        return f"Pin {self.id} - {self.local_title} ({self.content_object})"
