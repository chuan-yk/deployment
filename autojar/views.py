from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import CreateView, DeleteView, ListView
from fileupload.models import Fileupload
from cmdb.models import ProjectInfo
from .deploy import DeploySet
from django_redis import get_redis_connection


class deploy_list(ListView):
    model = Fileupload
    template_name = 'autojar/deploy_list.html'
    context_object_name = 'deploy_list'
    paginate_by = 10
    queryset = Fileupload.objects.filter(status=0,type=3).order_by('-create_date')

class history_list(ListView):
    model = Fileupload
    template_name = 'autojar/history_list.html'
    #context_object_name = 'history_list'
    paginate_by = 10
    queryset = Fileupload.objects.filter(status__in=(-1,2),type=3).order_by('-create_date')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(history_list, self).get_context_data(**kwargs)
        print(context)
        context['Rollback_info'] = Fileupload.objects.filter(status__in=(-1,2),type=3).order_by('-create_date')
        #print(context)
        return context



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
         action = request.GET.get('action')
         obj =  Fileupload.objects.get(id=id)
         fileobj = Fileupload.objects.get(id=id)

         redisObj = get_redis_connection('default')
         add_key = ("{pt}:{app}:{filename}".format(pt=fileobj.platform, app=fileobj.app,filename=fileobj.slug))

         if redisObj.exists(add_key):
            messages.error(request, '任务已经进入发布状态，请勿重新操作！', 'alert-danger')
            return redirect('/autojar/deploy_list/')
         else:
             redisObj.set(add_key,id+':'+fileobj.slug)

     else:
         messages.error(request, '无效的请求方法！', 'alert-danger')
         return redirect('/autojar/deploy_list/')
     if obj.type == 1:

         objdepy = DeploySet(obj.platform, obj.app, obj.name, obj.type)

     elif obj.type == 2:

        objdepy = DeploySet(obj.platform, obj.app, obj.name, obj.type)


     elif obj.type == 3:

        objdepy = DeploySet(id,obj.platform, obj.app, obj.name,obj.type)
        result = objdepy.jar(action)
        if len(result['Resultstderr'][0]) != 0:
            Fileupload.objects.filter(id=id).update(status=-1)
            messages.error(request, '发布失败！', 'alert-danger')
            redisObj.delete(add_key)
            return render(request, 'autojar/Result.html', result)
     Fileupload.objects.filter(id=id).update(status=2)
     messages.error(request, '发布成功！', 'alert-success')
     redisObj.delete(add_key)
     return render(request,'autojar/Result.html',result)




