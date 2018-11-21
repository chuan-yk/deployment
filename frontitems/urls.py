from django.conf.urls import url

from . import views

app_name = 'frontitems'
urlpatterns = [

    # url(r'^upload/$', views.upload, name='upload'),                                 # 原一键发布入口，弃用
    url(r'^list/$', views.list, name='list_all'),                                   # 列表详情
    url(r'^list/(?P<pk>[0-9]+)/detail/$', views.list_detail, name='file_detail'),   # 文件详情
    url(r'^pub/(?P<pk>[0-9]+)/do$', views.pub, name='do_pub'),                      # 执行发布任务
    url(r'^pub/(?P<pk>[0-9]+)/detail/$', views.pubresult, name='pub_detail'),        # 发布状态查看，发布进度和过程
    url(r'^pub/(?P<pk>[0-9]+)/return/$', views.pubreturn, name='pub_return'),        # 回滚接口,回滚上一个版本
]