from django.db import models

from committees.models import AssociationGroup

from .constants import ActivityType


class MeetingManager(models.Manager):
    def get_queryset(self):
        return super(MeetingManager, self).get_queryset().filter(parent_activity__type=ActivityType.ACTIVITY_MEETING)

    def filter_group(self, association_group: AssociationGroup):
        """Filters meetings for the given association_group"""
        return (
            super(MeetingManager, self)
            .get_queryset()
            .filter(parent_activity__organiserlink__association_group=association_group)
        )
