import os
from time import strftime
import uuid

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_safe

from .forms import LoginForm, RegisterForm
from .managers import TemplateManager
from .models import MarkdownImage

##################################################################################
# Contains render-code for displaying general pages.
# @since 15 JUL 2019
##################################################################################

@require_safe
def homePage(request):
    return render(request, 'core/home.html', {})

@require_safe
def logoutSuccess(request):
    if request.user.is_authenticated:
        return redirect(reverse('core/user_accounts/logout'))
    return render(request, 'core/user_accounts/logout-success.html', {})

@require_safe
@login_required
def viewNewsletters(request):
    return render(request, 'core/newsletters.html', {
        'NEWSLETTER_ARCHIVE_URL': settings.NEWSLETTER_ARCHIVE_URL,
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
            return redirect(reverse('core/user_accounts/register/success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = RegisterForm()

    return render(request, 'core/user_accounts/register/register.html', {'form': form})


##################################################################################
# Martor Image Uploader
# Based on: https://github.com/agusmakmun/django-markdown-editor/wiki

@login_required
@permission_required('core.can_upload_martor_images')
def markdown_uploader(request):
    """
    Makdown image upload for local storage
    and represent as json to markdown editor.
    """
    if request.method == 'POST' and request.is_ajax():
        if 'markdown-image-upload' in request.FILES:

            # Obtain POST data (object_id will be None if the object does not exist yet)
            object_id = request.POST.get('martor_image_upload_object_id', None)
            content_type_id = request.POST.get('martor_image_upload_content_type_id', None)

            # Verify POST data (valid content_type_id and object_id)
            try:
                content_type = ContentType.objects.get_for_id(content_type_id)
                if object_id is not None:
                    obj = content_type.get_object_for_this_type(id=object_id)
            except (ObjectDoesNotExist, ValueError):
                # Catch invalid ints or bogus data
                return HttpResponseBadRequest(_('Invalid request!'))

            # Can only upload MarkdownImages for specific models
            if f"{content_type.app_label}.{content_type.model}" not in settings.MARKDOWN_IMAGE_MODELS:
                return HttpResponseBadRequest(_('Invalid request!'))

            uploaded_file = request.FILES['markdown-image-upload']

            # Verify upload size
            if uploaded_file.size > settings.MAX_IMAGE_UPLOAD_SIZE:
                to_MB = settings.MAX_IMAGE_UPLOAD_SIZE / (1024 * 1024)
                data = {
                    'status': 400,
                    'error': _('Maximum image file is %(size) MB.') % {'size': to_MB}
                }
                return JsonResponse(data, status=400)

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
                # Pillow doesn't recognize it as an image.
                data = {
                    'status': 400,
                    'error': _('Bad image format.')
                }
                return JsonResponse(data, status=400)

            markdown_img = MarkdownImage.objects.create(
                uploader=request.user,
                content_type_id=content_type_id,
                object_id=object_id,
                image=uploaded_file
            )

            data = {
                'status': 200,
                'link':  markdown_img.image.url,
                'name': os.path.splitext(uploaded_file.name)[0]
            }
            return JsonResponse(data)
        return HttpResponseBadRequest(_('Invalid request!'))
    return HttpResponseBadRequest(_('Invalid request!'))
