import os
import subprocess
from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
#from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from datetime import datetime, date, timedelta
from .models import ProjectInfo, RecordOfStatic
from .pubstatic import ReplaceWorker, ReplaceWorker1
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone




@login_required
def upload(request):
    project_cn_set = set()
    platformlist = {}
    items=[]
    for project_cn in ProjectInfo.objects.values_list('project_cn'):
        project_cn_set.add(project_cn[0])
    for pjt_cn in project_cn_set:
        platformlist['{}'.format(pjt_cn)] = ProjectInfo.objects.filter(project_cn=pjt_cn)[0].project
        continue
    for i in set(ProjectInfo.objects.values_list('items')):
        items.append(i[0])
    platformlist = sorted(platformlist.items(), key=lambda obj: obj[1], reverse=True)
    items.sort()
    #platformlist = {'摩臣':"mc", '摩臣2':"mc2", '摩登':"md"}
    #items = ['sobet', 'lottery', 'lottery_m', 'sport']
    context = { 'platformlist': platformlist,  'items': items, }

    if request.method == "POST":  # 请求方法为POST时，进行处理
        try:
            pst_platform = request.POST.get('id')
            pst_item = request.POST.get('id2')
            myFile = request.FILES.get("myfile", None)  # 获取上传的文件，如果没有文件，则默认为None
            pst_filename = myFile.name
            task_projectinfo = ProjectInfo.objects.get(project=pst_platform, items=pst_item)
            if task_projectinfo.package_name != pst_filename:
                raise FileNotFoundError('Upload file = {}  does not match {}'.format(pst_filename, task_projectinfo.package_name))
            #inputfiledir = os.path.join(task_projectinfo.file_save_base_dir, datetime.now().strftime('%Y%m%d_%H%M%S'))
            inputfiledir = 'D:\\static'
            #os.makedirs(inputfiledir)
            fromfile = open(os.path.join(inputfiledir, myFile.name), 'wb+')
            for chunk in myFile.chunks():  # 分块写入文件
                fromfile.write(chunk)
            fromfile.close()
            print('===-======debug  1')
            print('==== 1.2 ', task_projectinfo.static_dir, os.path.join(inputfiledir, myFile.name), task_projectinfo.items, task_projectinfo.backup_file_dir)
            tasker = ReplaceWorker1(task_projectinfo.static_dir, os.path.join(inputfiledir, myFile.name), task_projectinfo.items, task_projectinfo.backup_file_dir)
            #tasker.ignore_newfile_run()
            #if tasker.coversuccess:
            print('===-======debug  2')
            coversuccess = True
            if coversuccess:    #tasker.coversuccess:
                messages.success(request, '发布成功！', 'alert-success')
                print('===-======debug  3')
                RecordOfStatic.objects.filter(items=task_projectinfo).update(isthis_current=False)
                record_task = task_projectinfo.recordofstatic_set.create(pub_time=timezone.now(),
                                                                         deployment_user=request.user.username,
                                                                         isthis_current=True, return_user='',
                                                                         upload_file=os.path.join(inputfiledir, myFile.name),
                                                                         backuplist=', '.join(tasker.backupdir),
                                                                         newdir=', '.join(tasker.newdirlist),
                                                                         newfile=', '.join(tasker.newfilelist),
                                                                         ignore_new=True, )
                print('===-======debug  4')
            else:
                messages.error(request, "发布失败，失败原因详见下文", 'alert-danger')
                context['task_error'] = 'tasker.errormessage'
            newfile_len = 1
            newdir_len = 2
            if newfile_len > 0 or newdir_len > 0:
                messages.warning(request, "默认新增文件不跟新，请联系运维或项目主管审核后更新", 'alert-danger' )
                context['newfiles'] = ['static/new/1.txt', '/static/new/mew.image.png'] #'tasker.newfilelist  '
                context['newdirs'] = ['static/newimage', 'static/download/']#'tasker.newdirlist'
        except AttributeError as e:   #myFile.name
            messages.error(request, '请选择更新文件', 'alert-danger')
        except FileNotFoundError as e:
            messages.error(request, '上传文件不正确\n{}'.format(str(e)), 'alert-danger')
        except ObjectDoesNotExist as e:
            messages.error(request, '请选择正确的平台-项目对应关系\n{}'.format(str(e)), 'alert-danger')
            print(e)
        except Exception as e:
            print(e)
            messages.error(request, '未知错误： '+str(e), 'alert-danger')
        finally:
            #return render(request, 'frontitems/upload.html', context)
            #return redirect(reverse(upload))
            pass

    elif request.method == 'GET':
        # if request.user.is_authenticated():
        #     #print(request.user.username, '====')
        #     pass
        #return HttpResponse(template.render(context, request))
        context = {'platformlist': platformlist, 'items': items, }
        return render(request,'frontitems/upload.html',context)