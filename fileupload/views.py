# encoding: utf-8
import json
from django.http import HttpResponse
from django.views.generic import CreateView, DeleteView, ListView
from .models import Fileupload,Application
from .response import JSONResponse, response_mimetype
from .serialize import serialize
from django.contrib.auth.mixins import LoginRequiredMixin


# def get_object(self, queryset=None):
#     obj = super().get_object(queryset=queryset)
#     if obj.author != self.request.user:
#         raise Http404()
#     return obj
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

class FileuploadCreateView(LoginRequiredMixin,CreateView):
    model = Fileupload
    #model = Application
    fields = ['file', 'platform', 'app', 'type', 'bug_id', 'description']
    # template_name_suffix = '_form'
    # template_name_ = 'fileupload/fileupload_form.html'
    def get_context_data(self, **kwargs):
        context = super(FileuploadCreateView,self).get_context_data(**kwargs)
        context['app_list'] = Application.objects.values_list('app_name',flat=True)
        return context

    def form_valid(self,form):
        try:
            form.instance.user = self.request.user.username
            form.instance.pt_name = Getplatform(self.request.POST['platform'])
        except:
            print('add form.instance  failure')
        self.object = form.save()
        files = [serialize(self.object)]

        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'
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
    #querySet = Picture.objects.all()
    #queryset = Picture.objects.filter(name='zhangsan')
    def render_to_response(self, context, **response_kwargs):

        files = [ serialize(p) for p in self.get_queryset() ]
        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response
