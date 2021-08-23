import os

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.utils import timezone
from django.utils.text import slugify

from membership_file.models import Member


__all__ = ['valid_item_class_ids', 'Ownership', 'Item', 'MiscellaneousItem']


class ItemManager(models.Manager):
    """ Manager for any object related to Item. Replaces standard manager in <Item>.objects """

    def get_all_in_possession(self):
        """ Returns all items currently in possession (owned or borrowed) """
        content_type = ContentType.objects.get_for_model(self.model)
        ownerships = Ownership.objects.filter(content_type=content_type, is_active=True)
        return self.get_queryset().filter(ownerships__in=ownerships).distinct()

    def get_all_owned(self):
        """ Returns all items owned by the association """
        content_type = ContentType.objects.get_for_model(self.model)
        ownerships = Ownership.objects.filter(content_type=content_type, is_active=True, group__isnull=False)
        return self.get_queryset().filter(ownerships__in=ownerships).distinct()

    def get_all_owned_by(self, member=None, group=None):
        """ Returns all items that are owned by the defined party """
        assert member or group

        content_type = ContentType.objects.get_for_model(self.model)
        ownerships = Ownership.objects.filter(content_type=content_type, is_active=True)
        if member:
            ownerships = ownerships.filter(member=member)
        if group:
            ownerships = ownerships.filter(group=group)
        return self.get_queryset().filter(ownerships__in=ownerships).distinct()


# File path to upload achievement images to
def get_item_image_upload_path(instance, filename):
    # Obtain extension
    # NB: A file can be renamed to have ANY extension
    _, extension = os.path.splitext(filename)

    item_name = f'{instance.id}-{slugify(instance.name)}'

    # file will be uploaded to MEDIA_ROOT / images/item/<item_type>/<id>.<file_extension>
    return 'images/item/{type_str}/{item_name}{extension}'.format(
        type_str=slugify(instance.__class__.__name__),
        item_name=item_name,
        extension=extension,
    )


class Item(models.Model):
    """ Item in the inventory system. Abstract root class.

    On permissions:
    There are several unique default permissions used for Items
    add_group_ownership_for_<item>: Allows users to add new ownerships to groups they are part of
    add_member_ownership_for_<item>: Allows users to add new ownerships to any active member
    maintain_ownerships_for_<item>: Adds additional control rights

    Furthermore the default permissions edit_<item> and delete_<item> are also used in the front-end

    This grants access to assigning items to groups or members respectively

    """
    name = models.CharField(max_length=128)
    description = models.TextField(max_length=512, blank=True, null=True)
    image = models.ImageField(upload_to=get_item_image_upload_path, blank=True, null=True)

    ownerships = GenericRelation('inventory.Ownership')
    # An achievement can also apply to roleplay items
    achievements = GenericRelation('achievements.AchievementItemLink')

    objects = ItemManager()

    class Meta:
        abstract = True
        ordering = ("name",)

        # Set the default permissions. Each item has a couple of addiotional default permissions
        default_permissions = ('add', 'change', 'delete', 'view',
                               'add_group_ownership_for',
                               'add_member_ownership_for',
                               'maintain_ownerships_for')

    @classmethod
    def get_item_contenttypes(cls):
        """ Returns all contenttypes for all items """
        content_types = []
        for item_class in cls.__subclasses__():
            content_types.append(ContentType.objects.get_for_model(item_class))
        return content_types

    def currently_in_possession(self):
        """ Returns all ownership items that are currently at the Knights """
        return self.ownerships.filter(is_active=True)

    def is_owned_by_association(self):
        """ Returns boolean stating whether this item is owned by the association """
        return self.ownerships.filter(is_active=True).filter(group__isnull=False).exists()

    def is_loaned_by_member(self):
        """ Returns boolean stating whether this item is owned by the association """

        return self.ownerships.filter(is_active=True).filter(member__isnull=False).exists()

    def __str__(self):
        return f'{self.__class__.__name__}: {self.name}'

    def other_fields(self):
        """ Returns a list of dicts with the model fields that are not defined in Item """
        other_fields = []
        exclude_names = ('id', 'name', 'description', 'image')
        for field in self._meta.local_fields:
            if field.name not in exclude_names:
                field_dict = {
                    'name': field.name,
                    'verbose_name': field.verbose_name,
                    'value': getattr(self, field.name),
                }
                # Set a value in case there are choices
                if hasattr(self, f'get_{field.name}_display'):
                    field_dict['display_value'] = getattr(self, f'get_{field.name}_display')()

                other_fields.append(field_dict)
        return other_fields


def valid_item_class_ids():
    """ Returns a query parameter for ids of valid Item classes. Used for Ownership Content type validity """
    valid_ids = []
    for content_type in Item.get_item_contenttypes():
        valid_ids.append(content_type.id)
    return {'id__in': valid_ids}


class Ownership(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True)

    added_since = models.DateField(default=timezone.now)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True,
                                    help_text="Whether item is currently at the Knights")
    note = models.TextField(max_length=256, blank=True, null=True)

    # The owned item
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to=valid_item_class_ids)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    @property
    def owner(self):
        """ Returns the owner of the item """
        if self.member:
            return self.member
        else:
            return self.group

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        # Make exlude a list to prevent complex if statements
        exclude = exclude or []

        if 'content_type' not in exclude and 'object_id' not in exclude:
            if self.content_object is None:
                raise ValidationError("The connected item does not exist", code='item_nonexistent')

    def clean(self):
        super(Ownership, self).clean()
        # Validate that EITHER member or group must be defined
        if self.member is None and self.group is None:
            raise ValidationError("Either a member or a group has to be defined", code='required')
        if self.member and self.group:
            raise ValidationError("An item can't belong both to a user and a group", code='invalid')

    def __str__(self):
        if self.member:
            return f'{self.content_object} supplied by {self.member}'
        else:
            return f'{self.content_object} owned ({self.group})'


class MiscellaneousItem(Item):
    pass


