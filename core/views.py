import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.http.response import Http404, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.http import require_safe

from .forms import RegisterForm
from .managers import TemplateManager
from .models import MarkdownImage

from dynamic_preferences.registries import global_preferences_registry
global_preferences = global_preferences_registry.manager()

##################################################################################
# Contains render-code for displaying general pages.
# @since 15 JUL 2019
##################################################################################

@require_safe
def logoutSuccess(request):
    if request.user.is_authenticated:
        return redirect(reverse('core:user_accounts/logout'))
    return render(request, 'core/user_accounts/logout-success.html', {})

@require_safe
@login_required
def viewNewsletters(request):
    share_link = global_preferences['newsletter__share_link']
    if not share_link:
        raise Http404("Newsletters are unavailable.")

    return render(request, 'core/newsletters.html', {
        'NEWSLETTER_ARCHIVE_URL': global_preferences['newsletter__share_link'],
    })


@require_safe
@login_required
def viewAccount(request):
    return render(request, 'core/user_accounts/account.html', {
        'included_template_name': TemplateManager.get_template('core/user_accounts/account.html'),
    })

@require_safe
def registerSuccess(request):
    return render(request, 'core/user_accounts/register/register_done.html', {})


def register(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RegisterForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # Save the user
            form.save(commit=True)
            return redirect(reverse('core:user_accounts/register/success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = RegisterForm()

    return render(request, 'core/user_accounts/register/register.html', {'form': form})


##################################################################################
# Martor Image Uploader
# Converted to class-based views, but based on:
#   https://github.com/agusmakmun/django-markdown-editor/wiki

class MartorImageUploadAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
        View for uploading images using Martor's Markdown Editor.

        Martor makes ajax requests to this endpoint when uploading images, and passes
        that uploaded image in addition to _all form contents_ of the form the editor
        is in. We're cheating by injecting hidden fields for content_type and object_id
        in such forms so we can access these values here.

        Martor expects these images to exist after calling this endpoint, meaning that
        they're immediately saved. However, the related object may not actually exist
        yet, as it may be new.
    """
    # There's no point in creating per-ContentType permissions, as users can just
    #   upload MarkdownImages for one ContentType they have permissions for and use
    #   that upload in another ContentType.
    permission_required = ('core.can_upload_martor_images',)
    raise_exception = True

    def _json_bad_request(self, message):
        """
            Return a JsonResponse with a status-code of 400 (Bad Request)
            and an error message.
        """
        data = {
            'status': 400,
            'error': message
        }
        return JsonResponse(data, status=400)

    def post(self, request, *args, **kwargs):
        # Must actually upload a file
        if 'markdown-image-upload' not in request.FILES:
            return self._json_bad_request('Could not find an uploaded file.')

        # Obtain POST data (object_id will be None if the object does not exist yet)
        object_id = request.POST.get('martor_image_upload_object_id', None)
        content_type_id = request.POST.get('martor_image_upload_content_type_id', None)

        # Verify POST data
        try:
            # Get the ContentType corresponding to the passed ID
            content_type = ContentType.objects.get_for_id(content_type_id)
            if object_id is not None:
                # Get the object for that ContentType
                obj = content_type.get_object_for_this_type(id=object_id)
        except (ObjectDoesNotExist, ValueError):
            # Catch invalid contentType-object combinatinos or bogus data
            return self._json_bad_request('Invalid content_type/object_id combination passed.')

        # Can only upload MarkdownImages for specific models
        if f"{content_type.app_label}.{content_type.model}" not in settings.MARKDOWN_IMAGE_MODELS:
            return self._json_bad_request("Cannot upload MarkdownImages for this model.")

        uploaded_file = request.FILES['markdown-image-upload']

        # Verify upload size
        if uploaded_file.size > settings.MAX_IMAGE_UPLOAD_SIZE:
            to_MB = settings.MAX_IMAGE_UPLOAD_SIZE / (1024 * 1024)
            return self._json_bad_request('Maximum image file size is %(size)s MB.' % {'size': str(to_MB)})

        ##############
        ## BEGINCOPY
        # Copied from Django's ImageField.to_python(..)
        #
        # Use Pillow to verify that a valid image was uploaded (just like in ImageField)
        # NB: Pillow cannot identify this in all cases. E.g. html files with valid png headers
        #   see: https://docs.djangoproject.com/en/3.1/topics/security/#user-uploaded-content-security
        from PIL import Image

        try:
            # load() could spot a truncated JPEG, but it loads the entire
            # image in memory, which is a DoS vector. See #3848 and #18520.
            image = Image.open(uploaded_file)
            # verify() must be called immediately after the constructor.
            image.verify()
        except Exception as exc:
            return self._json_bad_request(_('Bad image format.'))
        #
        ## ENDCOPY
        ##############

        # Create a new MarkdownImage for the uploaded image
        markdown_img = MarkdownImage.objects.create(
            uploader=request.user,
            content_type_id=content_type_id,
            object_id=object_id,
            image=uploaded_file
        )

        # Everything was okay; report back to Martor
        return JsonResponse({
            'status': 200,
            'link':  markdown_img.image.url,
            'name': os.path.splitext(uploaded_file.name)[0]
        })

def show_error_403(request, exception=None):
    return render(request, 'core/errors/error403.html', status=403)


def show_error_404(request, exception=None):
    return render(request, 'core/errors/error404.html', status=404)
