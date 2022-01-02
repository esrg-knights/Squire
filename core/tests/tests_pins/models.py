from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.pin_models import PinVisualiserBase, PinnableModelMixin


class BlogPost(models.Model):
    """ Test Model used to test PinnableModelMixin. """
    title = models.CharField(max_length=55)
    content = models.TextField()
    for_date = models.DateTimeField(default=timezone.now)
    publishes_on = models.DateTimeField(default=timezone.now)


class BlogCommentPinVisualiser(PinVisualiserBase):
    """ Visualiser for pins with a BlogComment attached to them """

    # Database fieldnames
    pin_date_query_fields = ('blog_post__for_date',)
    pin_publish_query_fields = ('publish_date', 'blog_post__publishes_on',)
    pin_expiry_query_fields = () # No expiry date for this model

    # Attributes
    pin_description_field = "content" # Normal field
    pin_url_field = "url" # Property

    def get_pin_title(self, pin): # Method
        return "Comment on " + self.instance.blog_post.title

    def get_pin_date(self, pin):
        return self.instance.blog_post.for_date

    def get_pin_publish_date(self, pin):
        return self.instance.publish_date or self.instance.blog_post.publishes_on

class BlogComment(PinnableModelMixin, models.Model):
    """ Test model used to test PinnableModelMixin """
    pin_visualiser_class = BlogCommentPinVisualiser

    content = models.TextField()
    publish_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")

    @property
    def url(self):
        # This is obviously a very bad practise, but this is a test model :D
        return f"/blogs/{self.blog_post.id}/comments/{self.id}"

    def clean_pin(self, pin):
        if "schaduwbestuur" in self.content:
            raise ValidationError({'object_id':
                "Fake news is not permitted."
            })
