from django.db import models
from django.contrib.auth.models import Group



class AssociationGroup(models.Model):
    site_group = models.OneToOneField(Group, on_delete=models.CASCADE)
    shorthand = models.CharField(max_length=16)
    icon = models.ImageField(upload_to='images/committees/', blank=True, null=True)

    COMMITTEE = 'C'
    ORDER = 'O'
    WORKGROUP = 'WG'
    BOARD = 'B'
    GROUPTYPES = [
        (COMMITTEE, 'Committee'),
        (ORDER, 'Order'),
        (WORKGROUP, 'Workgroup'),
        (BOARD, 'Board'),
    ]
    type = models.CharField(max_length=2, choices=GROUPTYPES)
    is_public = models.BooleanField(default=False)

    short_description = models.CharField(max_length=128, blank=True, null=True)
    long_description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ("shorthand",)

    @property
    def name(self):
        return self.site_group.name

    def __str__(self):
        return self.site_group.name
