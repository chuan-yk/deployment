from django.conf.urls import url

from . import views

app_name = 'domains'
urlpatterns = [
    url(r'^init/$', views.tmp_analysis, ),                              # 临时初始化
    url(r'^node/$', views.node_index, name='node'),                     # 解析IP列表
    url(r'^node/(?P<pk>\d+)/edit/$', views.node_edit, name='edit'),     # 解析IP详情编辑
    url(r'^node/add/$', views.node_add, name='node_add'),                   # 新增解析IP
    url(r'^node/import/$', views.node_import, name='node_import'),      # 解析IP列表导入
    url(r'^node/export/$', views.node_export, name='node_export'),      # 解析IP列表导出
    url(r'^primarydomain/$', views.primary, name='primary'),            # 域名资产列表
    url(r'^primarydomain/import/$', views.pry_import, name='primary_domain_import'),            # 域名资产列表
    url(r'^primarydomain/export/$', views.pry_export, name='primary_domain_export'),            # 域名资产列表
    url(r'^primarydomain/(?P<pk>\d+)/edit/$', views.primary_edit, name='primary_domain_edit'),      # 域名资产编辑
    url(r'^primarydomain/add/$', views.pry_add, name='primary_domain_add'),      # 域名资产新增
    url(r'^list/$', views.domain_list, name='domain_list'),             # 所有域名列表
    url(r'^list/ssl/$', views.domain_list_ssl, name='domain_list_ssl'),             # 所有SSL域名列表
    url(r'^list/(?P<pk>\d+)/edit/$', views.domain_edit, name='domain_edit'),    # 域名信息编辑
    url(r'^list/add/$', views.domain_add, name='domain_add'),           # 域名信息新增
    url(r'^list/ssl/(?P<pk>\d+)/flush/$', views.domain_ssl_flush, name='domain_ssl_flush'),       # 域名信息更新
]