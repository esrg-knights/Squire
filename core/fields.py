from core.models import MarkdownImage
from django.db import models
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from martor.fields import MartorFormField
from martor.utils import markdownify

__all__ = ['MarkdownObject', 'MarkdownFieldMixin', 'MarkdownCharField', 'MarkdownTextField']

class MarkdownObject:
    """
        A wrapper object for strings containing Markdown. Contains methods
        for rendering, stripping, and displaying as raw Markdown.
    """
    def __init__(self, raw_value):
        self.raw_value = raw_value

    def __str__(self):
        # Django uses str() often for conversions as default beahviour
        #   https://docs.djangoproject.com/en/2.2/howto/custom-model-fields/#some-general-advice
        return self.raw_value

    def __len__(self):
        # For max_length and friends
        return len(self.raw_value)

    def __eq__(self, other):
        if isinstance(other, MarkdownObject):
            return self.raw_value == other.raw_value
        return False

    def as_rendered(self):
        """
            Returns the Markdown in html format.  E.g. <b>bold text</b>
            Tags not compiled by Markdown are escaped, meaning that it is safe to use.
        """
        return mark_safe(markdownify(self.raw_value))

    def as_raw(self):
        """ Returns the Markdown in its native syntax. E.g. **bold text** """
        return self.raw_value

    def as_plaintext(self):
        """ Returns the Markdown with its html tags stripped. E.g. <**bold text**> becomes <bold text>.
            Note that some text may lose meaning this way.
            For example, <click [here](https://kotkt.nl)> becomes <click here>
        """
        return mark_safe(strip_tags(self.as_rendered()))

class MarkdownFieldMixin:
    """
        Mixin to be used by other model fields that converts text to
        MarkdownObjects (and vice versa).
        Should only be used for model fields that natively store text,
        such as CharField or TextField.
    """
    def to_python(self, value):
        if isinstance(value, MarkdownObject) or value is None:
            return value
        return MarkdownObject(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return MarkdownObject(str(value))

    def get_prep_value(self, md_object: MarkdownObject):
        if md_object is None:
            return None
        if isinstance(md_object, str):
            # According to the docs, md_object should always be a Python instance of our model.
            #   However, for some reason, passing in empty values in forms causes it to be the
            #   empty string, and I have no clue why... Using .create(..) syntax causes the same problem.
            #   to_python(..) and from_db_value always return an MDObject.
            #   https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/#converting-python-objects-to-query-values
            return md_object
        return md_object.raw_value

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def formfield(self, **kwargs):
        # Note: There's no point in using ImageUploadMartorWidget here, as that
        #   requires the user of the view and the model using this field,
        #   which we don't actually know here
        defaults = {'form_class': MartorFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

class MarkdownCharField(MarkdownFieldMixin, models.CharField):
    """ CharField that allows Markdown """
    description = "Raw Markdown (up to %(max_length)s)"

class MarkdownTextField(MarkdownFieldMixin, models.TextField):
    """ TextField that allows Markdown """
    description = "Raw Markdown"
