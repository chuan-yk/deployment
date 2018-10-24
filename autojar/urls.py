from django.conf.urls import url
from . import views

app_name = 'autojar'
urlpatterns = [
    url(r'^upload/$', views.upload_file, name='jar_upload'),
]