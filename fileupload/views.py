# encoding: utf-8
import json
from django.http import HttpResponse
from django.views.generic import CreateView, DeleteView, ListView
from .response import JSONResponse, response_mimetype
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist

from .serialize import serialize
from .models import Fileupload
from cmdb.models import ProjectInfo


def Getplatform(name):
    if name == 'mc':
        ptname = '摩臣'
    elif name == 'md':
        ptname = '摩登'
    elif name == 'cyq':
        ptname = '彩友圈'
    else:
        return 'Unknow'
    return ptname


class FileuploadCreateView(LoginRequiredMixin, CreateView):
    model = Fileupload
    fields = ['file', 'platform', 'app', 'type', 'bug_id', 'description']

    # template_name_suffix = '_form'
    # template_name_ = 'fileupload/fileupload_form.html'
    def get_context_data(self, **kwargs):
        context = super(FileuploadCreateView, self).get_context_data(**kwargs)
        context['app_list'] = ProjectInfo.objects.values_list('items', flat=True).distinct().order_by('items')
        context['pt_list'] = ProjectInfo.objects.values('platform', 'platform_cn').distinct()
        return context

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user.username
            form.instance.pt_name = Getplatform(self.request.POST['platform'])
            form.instance.project = ProjectInfo.objects.get(platform=self.request.POST['platform'],
                                                            items=self.request.POST['app'],
                                                            type=self.request.POST['type'], )
        except ObjectDoesNotExist as e:
            # messages.error(self.request, "没有对应项目", 'alert-danger')
            data = json.dumps({'error': True, 'message': "没有对应项目"})
            return HttpResponse(content=data, status=400, content_type='application/json')
        self.object = form.save()
        files = [serialize(self.object)]
        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'  # MIME 协议的扩展，MIME 协议指示 MIME 用户代理如何显示附加的文件
        return response

    def form_invalid(self, form):
        data = json.dumps(form.errors)
        return HttpResponse(content=data, status=400, content_type='application/json')


class FileuploadDeleteView(DeleteView):
    model = Fileupload

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        response = JSONResponse(True, mimetype=response_mimetype(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response


class FileuploadListView(ListView):
    model = Fileupload

    # querySet = Picture.objects.all()
    # queryset = Picture.objects.filter(name='zhangsan')
    def render_to_response(self, context, **response_kwargs):
        files = [serialize(p) for p in self.get_queryset()]
        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response
