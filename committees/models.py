import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models

from core.fields import MarkdownTextField
from membership_file.models import Member


class AssociationGroup(models.Model):
    site_group = models.OneToOneField(Group, on_delete=models.CASCADE)
    shorthand = models.CharField(max_length=16, blank=True, null=True)
    icon = models.ImageField(upload_to='images/committees/', blank=True, null=True)

    COMMITTEE = 'C'
    GUILD = 'O'
    WORKGROUP = 'WG'
    BOARD = 'B'
    GROUPTYPES = [
        (COMMITTEE, 'Committee'),
        (GUILD, 'Order'),
        (WORKGROUP, 'Workgroup'),
        (BOARD, 'Board'),
    ]
    type = models.CharField(max_length=2, choices=GROUPTYPES)
    is_public = models.BooleanField(default=True)

    short_description = models.CharField(max_length=128, blank=True, null=True)
    long_description = models.TextField(blank=True, null=True)

    # Internal data
    members = models.ManyToManyField(
        Member,
        through='AssociationGroupMembership',
    )

    contact_email = models.EmailField(null=True, blank=True)
    instructions = MarkdownTextField(blank=True, null=True, max_length=2047,
                                    help_text="Information displayed on internal info page")

    class Meta:
        ordering = ("shorthand",)
        permissions = [
            ("can_view_committee_members", "Can view committee members"),
            ("can_view_order_members", "Can view order members"),
            ("can_view_board_members", "Can view board members"),
        ]

    @property
    def name(self):
        return self.site_group.name

    def __str__(self):
        return self.site_group.name


class GroupExternalUrl(models.Model):
    """ Model class to create quick urls on group screens """
    association_group = models.ForeignKey(AssociationGroup, on_delete=models.CASCADE, related_name='shortcut_set')
    name = models.CharField(max_length=32)
    url = models.URLField()
    description = models.CharField(max_length=63, null=True, blank=True)

    def __str__(self):
        return f'{self.association_group.name} - {self.name}'


class AssociationGroupMembership(models.Model):
    """
    This is an alternative to the django user-group connection. For one we can't assume that a member has a user account
    For another we want additional information stored that is difficult when attempting to override the link between
    user and group.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)
    external_person = models.CharField(max_length=64, help_text="Name of a person who is not a registered member", blank=True)
    group = models.ForeignKey(AssociationGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=32, blank=True, default="",
                            help_text="Name of the formal role. E.g. treasurer, president")
    title = models.CharField(max_length=64, blank=True, default="",
                             help_text="Symbolic name (if any) e.g. 'God of War', 'Minister of Alien affairs', or 'Wondrous Wizard'")
    joined_since = models.DateField(default=datetime.date.today)

    class Meta:
        unique_together = [['member', 'group']]
        ordering = ['-role', 'member__legal_name']

    def clean(self):
        if not (self.member or self.external_person):
            raise ValidationError("Either a member or an external person name needs to be defined", code='required')
        if self.member and self.external_person:
            raise ValidationError("You can not have both a member and external person connected", code='fields_conflict')

    @property
    def member_name(self):
        """ Returns the name of the member, no matter the type of connection """
        if self.member:
            return str(self.member)
        else:
            return self.external_person

