
from django.shortcuts import render, redirect

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from tempfile import NamedTemporaryFile
from django.views.generic import CreateView, DeleteView, ListView
from fileupload.models import Fileupload
from django.http import HttpResponse
from .deploy import DeploySet
from django_redis import get_redis_connection


class deploy_list(ListView):
    model = Fileupload
    template_name = 'autojar/deploy_list.html'
    context_object_name = 'deploy_list'
    paginate_by = 3
    queryset = Fileupload.objects.filter(status=0,type__in=(1,2,3)).order_by('-create_date')



def delfile(request):
    if request.method == 'GET':
        try:
            ID = request.GET.get('id', default=0)
            Fileupload.objects.filter(id=ID).delete()
            messages.success(request, '删除成功！', 'alert-success')
        except:
            messages.error(request, '删除失败！', 'alert-danger')
    return redirect('/autojar/deploy_list/')




def RunEnter(request):
     if request.method == "GET":
         id = request.GET.get('id')
         obj =  Fileupload.objects.get(id=id)
         fileobj = Fileupload.objects.get(id=id)
         redisObj = get_redis_connection('default')
         add_key = ("{pt}:{app}:{type}_{id}"
                 .format(pt=fileobj.platform, app=fileobj.app, type=fileobj.type, id=id))

         redis_lock = redisObj.get(add_key)

         if redisObj.exists(add_key):
            messages.error(request, '任务已经进入发布状态，请勿重新操作！', 'alert-danger')
            return redirect('/autojar/deploy_list/')
         else:
             redisObj.set(add_key,id)
     else:
         messages.error(request, '无效的请求方法！', 'alert-danger')
         return redirect('/autojar/deploy_list/')
     if obj.type == 1:
         print(obj.type)
         objdepy = DeploySet(obj.platform, obj.app, obj.name, obj.type)

     elif obj.type == 2:
        print(obj.type)
        objdepy = DeploySet(obj.platform, obj.app, obj.name, obj.type)


     elif obj.type == 3:
        print(obj.type)
        objdepy = DeploySet(obj.platform, obj.app, obj.name, obj.type)
        result = objdepy.jar()
        print(result)

     Fileupload.objects.filter(id=id).update(status=2)
     return render(request,'autojar/Result.html',result)





