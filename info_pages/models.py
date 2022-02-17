from django.db import models

class InfoPage(models.Model):
    """
    #TODO
    """

    title = models.CharField(max_length=100, default='test title')
    description = models.TextField()
    link = models.URLField(blank=True, null=True)

    