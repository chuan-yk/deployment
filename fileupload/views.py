# encoding: utf-8
import json
from django.http import HttpResponse
from django.views.generic import CreateView, DeleteView, ListView
from .models import Fileupload
from .response import JSONResponse, response_mimetype
from .serialize import serialize
from django.contrib.auth.mixins import LoginRequiredMixin



class FileuploadCreateView(LoginRequiredMixin,CreateView):
    model = Fileupload
    # fields = ['file','app','bug_id','description']
    # fields = ['all']
    fields = '__all__'
    # template_name_suffix = '_form'
    # template_name_ = 'fileupload/fileupload_form.html'

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
        except:
            pass

        self.object = form.save()
        files = [serialize(self.object)]
        print(files)
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
