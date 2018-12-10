from django.conf.urls import url
from . import views


app_name = 'autojar'
urlpatterns = [

    url(r'delfile/$', views.delfile, name='del_file'),
    url(r'^deploy_list/$',views.deploy_list.as_view(), name='deploy_list'),
    url(r'^history_list/$',views.history_list.as_view(), name='history_list'),
    url(r'RunEnter/$', views.RunEnter, name='RunEnter'),

]