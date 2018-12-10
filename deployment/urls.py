"""deployment URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,include
from django.contrib import admin
from django.contrib.auth import views as auth
from django.contrib.auth.decorators import login_required
from . import views
from django.urls import include, path
from django.http import HttpResponseRedirect
from django.views.generic.base import RedirectView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^users/login/$', auth.login, {'template_name': 'login.html'}, name='login'),
    url(r'^users/logout/$', auth.logout, {'next_page': '/'}, name='logout'),
    url(r'^users/change_password/$', login_required(auth.password_change), {'post_change_redirect' : '/','template_name': 'change_password.html'}, name='change_password'),
    url(r'^frontitems/', include('frontitems.urls')),
    url(r'^autojar/', include('autojar.urls')),
    url(r'^$', views.indexpage, name='indexhome'),
    url(r'coming_soon$', views.comingsoon, name='not_finish_page'),
    url(r'frontapp/', include('frontapp.urls')),
    url(r'tomcatwar/', include('tomcatwar.urls')),
    url(r'tomcatzip/', include('tomcatzip.urls')),
    url(r'tomcatjar/', include('tomcatjar.urls')),
    path('upload/', include('fileupload.urls')),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/img/favicon.ico')),
]
