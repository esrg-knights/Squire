from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout
from .forms import LoginForm, RegisterForm
from django.shortcuts import redirect
from django.urls import reverse

# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_safe

# User must be logged in to access a page
from django.contrib.auth.decorators import login_required


##################################################################################
# Contains render-code for displaying general pages.
# @since 15 JUL 2019
##################################################################################

class TemplateManager():
    # Stores the method used to display a user's name
    templates = {}

    # Allows other modules to change the way a user is displayed across the entire application
    @staticmethod
    def set_template(filename, template_name):
        TemplateManager.templates[filename] = template_name

    @staticmethod
    def get_template(filename):
        if filename in TemplateManager.templates:
            return TemplateManager.templates[filename]
        return None


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
