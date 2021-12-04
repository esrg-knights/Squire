import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.http.response import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.http import require_safe
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from .forms import PinnableForm, RegisterForm
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


class AccountTabsMixin:
    tab_name = None

    def get_context_data(self, *args, **kwargs):
        context = super(AccountTabsMixin, self).get_context_data(*args, **kwargs)
        context[self.tab_name] = True
        context['tabs'] = self.get_tab_data()
        return context

    def get_tab_data(self):
        tabs = [
            {'name': 'tab_account', 'verbose': 'Account', 'url_name': 'core:user_accounts/account'},
            {'name': 'tab_membership', 'verbose': 'Membership', 'url_name': 'membership_file/membership'},
            {'name': 'tab_preferences', 'verbose': 'Preferences', 'url_name': 'user_interaction:change_preferences'},
        ]
        for tab in tabs:
            if tab['name'] == self.tab_name:
                tab['selected'] = True
        return tabs


class AccountView(AccountTabsMixin, TemplateView):
    """ Base account page """
    template_name = "core/user_accounts/account_info.html"
    tab_name = 'tab_account'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context[self.tab_name] = True
        return context

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

##################################################################################
# Pin Creation

class PinnableFormView(PermissionRequiredMixin, FormView):
    """
        View that handles instantiation of a form to create a
        pin for a specific model instance.
    """
    form_class = None # Passed when instantiated
    permission_required = ('core.add_pin', 'core.delete_pin')

    def setup(self, request, obj, *args, **kwargs):
        self.object = obj
        return super().setup(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(user=self.request.user, obj=self.object)
        return kwargs

    def form_valid(self, form):
        pin = form.save()
        if form.cleaned_data['do_pin']:
            message = _("'{pinnable_obj}' was successfully pinned!")
        else:
            message = _("'{pinnable_obj}' was successfully unpinned!")
        messages.success(self.request, message.format(pinnable_obj=self.object.get_pin_message_name(pin).capitalize()))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, f"An unexpected error occurred when trying to pin {str(self.object)}. Please try again later.")
        return super().form_invalid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class PinnablesMixin:
    """
    Mixin that adds a form to the view that allows pinning a model instance
    currently in the View. It can be used alongside any other form in the
    same View.

    Multiple pinnable objects can exist in the same view, and their respective
    forms can be identified using their ContentType and index.

    `pinnable_formview_class` (`PinnableFormView` by default) handles form
    instantiation, and was split up 1) to keep logic separate, and 2) to
    ensure that another form in a View inheriting this Mixin does not get
    overridden by a form for a pinnable.
    """
    pinnable_formview_class = PinnableFormView
    pinnable_form_class = PinnableForm

    def post(self, request, *args, **kwargs):
        for objs in self.get_pinnable_objects():
            for i, obj in enumerate(objs):
                prefix = self.get_prefix_for_pinnable(obj, i)
                # Was this pinnable (un)pinned?
                if prefix in self.request.POST:
                    view = self.pinnable_formview_class.as_view(
                        form_class=self.get_form_class_for_pinnable(obj),
                        prefix=prefix
                    )
                    # Pass the object to the view
                    return view(request, obj, *args, **kwargs)

        # The "pin" form was not submitted; so another form was
        #   submitted instead. Call the parent's post method instead.
        if hasattr(super(), "post"):
            return super().post(request, *args, **kwargs)

        # Fallback in case the parent does not have a post method.
        messages.error(self.request, f"Pin data was corrupted. Please try again later.")
        return HttpResponseRedirect(self.request.get_full_path())

    def get_pinnable_objects(self):
        """
            Get the model instances that can be (un)pinned in this View. The return value
            must be an iterable of iterables (e.g., a list of tuples: `[(obj1, obj2, ...), ...]`),
            where all objects in each nested iterable are of the same type.

            For example, to return both users and groups to (un)pin, one can use:
            `[(user1, user2), (group1, group2, group3)]`

            Model instances do not need to exist in the database when they are passed here,
            although they will be saved once they are pinned.
        """
        raise NotImplementedError("Subclasses of PinnablesMixin should override get_pinnable_objects()")

    def is_pinnable_pinned(self, obj):
        return obj.pins.exists()

    def get_prefix_for_pinnable(self, obj, i):
        """ The prefix used to identify the i'th object of its type """
        # pinnable_form-<content_type_id>-<index>
        return f"pinnable_form-{ContentType.objects.get_for_model(obj).pk}-{i}"

    def get_form_class_for_pinnable(self, obj):
        return self.pinnable_form_class

    def get_context_data(self, **kwargs):
        """ Insert the pinnable forms into the context dict. """
        context = super().get_context_data(**kwargs)
        for objs in self.get_pinnable_objects():
            for i, obj in enumerate(objs):
                prefix = self.get_prefix_for_pinnable(obj, i)
                form_kwargs = {
                    'initial': {'do_pin': not self.is_pinnable_pinned(obj)},
                    'prefix': prefix,
                    'user': self.request.user,
                    'obj': obj,
                }
                context[prefix] = self.get_form_class_for_pinnable(obj)(**form_kwargs)
        return context
