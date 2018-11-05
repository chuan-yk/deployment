# encoding: utf-8
from django.urls import path
from fileupload.views import (FileuploadCreateView, FileuploadDeleteView, FileuploadListView)


urlpatterns = [

    path('new/',FileuploadCreateView.as_view(), name='upload-new'),
    path('delete/<int:pk>',FileuploadDeleteView.as_view(), name='upload-delete'),
    path('view/',FileuploadListView.as_view(), name='upload-view'),
]
