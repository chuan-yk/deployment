from django.conf.urls import url

from . import views

app_name = 'tmct_zip_url_tag'
urlpatterns = [
    url(r'^list/$', views.IndexView.as_view(), name='list_all'),  # 列表详情
    url(r'^list/(?P<pk>[0-9]+)/detail/$', views.list_detail, name='file_detail'),   # 文件详情
    url(r'^pub/(?P<pk>[0-9]+)/do$', views.apppub, name='do_pub'),                      # 执行发布任务
    url(r'^pub/(?P<pk>[0-9]+)/return/$', views.approllback, name='pub_return'),  # 回滚接口,回滚上一个版本
]
