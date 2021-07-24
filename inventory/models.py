import datetime

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentTypeManager, ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from membership_file.models import Member


class Item(models.Model):
    """ Item in the inventory system. Abstract root class. """
    name = models.CharField(max_length=128)
    note = models.TextField(max_length=512, blank=True, null=True)

    ownerships = GenericRelation('Ownership')

    class Meta:
        abstract = True

    def currently_in_possession(self):
        return self.ownerships.filter(is_active=True).count()

    def __str__(self):
        return f'{self.__class__.__name__}: {self.name}'


class BoardGame(Item):
    """ Defines boardgames """
    bgg_id = models.IntegerField(blank=True, null=True)


def valid_item_class_ids():
    """ Returns a query parameter for ids of valid Items """
    valid_ids = []
    for content_type in ContentType.objects.all():
        if issubclass(content_type.model_class(), Item):
            valid_ids.append(content_type.id)
    return {'id__in': valid_ids}


class Ownership(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True)

    added_since = models.DateField(default=datetime.date.today)
    is_active = models.BooleanField(default=True,
                                    help_text="Whether item is currently at the Knights")

    # The owned item
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to=valid_item_class_ids)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def clean(self):
        super(Ownership, self).clean()
        if self.member is None and self.group is None:
            raise ValidationError("Either a member or a group has to be defined", code='required')
        if self.member and self.group:
            raise ValidationError("An item can't belong both to a user and a group", code='invalid')

