from django.db import models
from django.contrib.auth.models import Group



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
        (GUILD, 'Guild'),
        (WORKGROUP, 'Workgroup'),
        (BOARD, 'Board'),
    ]
    type = models.CharField(max_length=2, choices=GROUPTYPES)
    is_public = models.BooleanField(default=True)

    short_description = models.CharField(max_length=128, blank=True, null=True)
    long_description = models.TextField(blank=True, null=True)


    # Internal data
    instructions = models.TextField(blank=True, null=True, max_length=2047)

    class Meta:
        ordering = ("shorthand",)

    @property
    def name(self):
        return self.site_group.name

    def __str__(self):
        return self.site_group.name


class GroupExternalUrls(models.Model):
    """ Model class to create quick urls on group screens """
    association_group = models.ForeignKey(AssociationGroup, on_delete=models.CASCADE, related_name='shortcut_set')
    name = models.CharField(max_length=32)
    url = models.URLField()
    description = models.CharField(max_length=63, null=True, blank=True)

    def __str__(self):
        return f'{self.association_group.name} - {self.name}'
