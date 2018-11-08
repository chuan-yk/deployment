from django.conf.urls import url

from . import views

app_name = 'frontitems'
urlpatterns = [

    url(r'^upload/$', views.upload, name='upload'),
    url(r'^list/$', views.list, name='list_all'),
    url(r'^list/(?P<pk>[0-9]+)/detail/$', views.list_detail, name='list_pub'),
    #url(r'^pub/(?P<pk>[0-9]+)/do$', views.pub, name='do_pub'),
    #url(r'^pub/(?P<pk>[0-9]+)/result$', views.pubresult, name='pub_result'),

]