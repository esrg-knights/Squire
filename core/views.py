from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from .forms import LoginForm

# @require_post only accepts HTTP POST requests
# @require_safe only accepts HTTP GET and HEAD requests
from django.views.decorators.http import require_POST, require_safe, require_http_methods

# User must be logged in to access a page
from django.contrib.auth.decorators import login_required


##################################################################################
# Contains render-code for displaying general pages.
# @author E.M.A. Arts
# @since 15 JUL 2019
##################################################################################

@require_safe
def homePage(request):
    return render(request, 'core/home.html', {})

@require_safe
def logoutSuccess(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/logout')
    return render(request, 'core/user_accounts/logout-success.html', {})


@require_safe
@login_required
def viewAccount(request):
    return render(request, 'core/user_accounts/account.html', {})