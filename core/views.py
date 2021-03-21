import os
from time import strftime
import uuid

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_safe

from .forms import LoginForm, RegisterForm
from .managers import TemplateManager

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
@staff_member_required # TODO: Utilise Django's permission system
def markdown_uploader(request):
    """
    Makdown image upload for local storage
    and represent as json to markdown editor.
    """
    if request.method == 'POST' and request.is_ajax():
        if 'markdown-image-upload' in request.FILES:
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

            img_uuid = "{1}-{0}.{2}".format(uuid.uuid4().hex[:10], strftime("%H%M%S"), image.format.lower())
            storage_path = os.path.join(settings.MARTOR_UPLOAD_PATH,
                str(request.user.id), strftime("%Y{0}%m{0}%d".format(os.path.sep)), img_uuid)
            default_storage.save(storage_path, uploaded_file)
            img_url = os.path.join(settings.MEDIA_URL, storage_path)

            data = {
                'status': 200,
                'link': img_url,
                'name': uploaded_file.name
            }
            return JsonResponse(data)
        return HttpResponseBadRequest(_('Invalid request!'))
    return HttpResponseBadRequest(_('Invalid request!'))
