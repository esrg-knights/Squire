from django.db import models
from django.contrib.auth.models import Group



class AssociationGroup(Group):
    shorthand = models.CharField(max_length=16)
    icon = models.ImageField(upload_to='images/committees/')

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

    short_description = models.CharField(max_length=128)
    long_description = models.TextField()



