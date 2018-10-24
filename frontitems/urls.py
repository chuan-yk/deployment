from django.conf.urls import url

from . import views

app_name = 'frontitems'
urlpatterns = [
    #url(r'^$', views.index, name='home'),
    #url(r'^static/$', views.index, name='domain'),
    #url(r'^upload/(?P<plfmid>.+)/(?P<items>.+)/$', views.upload, name='upload'),
    url(r'^upload/$', views.upload, name='upload'),
]