import os
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
import threading
from datetime import datetime, date, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from fileupload.models import Fileupload
from .remotepubstatic import RemoteReplaceWorker
from cmdb.models import ServerInfo, ProjectInfo


@login_required
def list(request):
    """静态文件全部内容列表
       Fileupload: 0 为静态文件
    """
    static_uploadfile_list = Fileupload.objects.filter(type=0)
    return render(request, 'frontitems/list.html', {'static_uploadfile_list': static_uploadfile_list})


@login_required
def list_detail(request, pk):
    """指定pk 文件详情, Get参数filemd5 为1: 显示更新文件MD5 信息，"""
    if request.GET.get('filemd5') == '1':
        show = True
        MD5 = {'f1': '1111111', 'f2': '22222222', 'f3': '3333333333'}
    else:
        show = False
        MD5 = {'None': None}

    uploadfile_detail = Fileupload.objects.get(pk=pk)
    # pub_lock   = ''  # function return
    pub_lock = {'lock': False, 'pubtask': 'mc_sobet_jar_20181108_0001'}
    filemd5 = {'show': show, 'MD5': MD5}
    context = {'uploadfile_detail': uploadfile_detail, 'pub_lock': pub_lock, 'filemd5': filemd5}
    print(context['filemd5'])
    return render(request, 'frontitems/file_detail.html', context)


@login_required
def pub(request, pk):
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                   type=pub_file.type)
    serverinfo_instance = pjt_info.ipaddress
    dstdir = pjt_info.dst_file_path
    fromfile = pub_file.file.path
    platfrom = pjt_info.platform
    items = pjt_info.items
    backupdir = pjt_info.backup_file_dir
    pub_task = RemoteReplaceWorker(serverinfo_instance, dstdir, fromfile, platfrom, items, backupdir, )
    print( pub_task._dstdir, pub_task._backup_ver )

    return HttpResponse('it is ok , test')


@login_required
def pubresult(request, pk):
    pass


@login_required
def run_tasker(task_projectinfo, inputfiledir):
    tasker = RemoteReplaceWorker(serverinfo_instance='==',
                                 dstdir=task_projectinfo.static_dir,
                                 fromfile=os.path.join(inputfiledir, myFile.name),
                                 platfrom=task_projectinfo.project,
                                 items=task_projectinfo.items,
                                 backupdir=task_projectinfo.backup_file_dir, )
    import time
    time.sleep(10)
    # tasker.ignore_newfile_run()


@login_required
def upload(request):  # 原一键发布入口，弃用
    project_cn_set = set()
    platformlist = {}
    items = []
    for project_cn in ProjectInfo.objects.values_list('project_cn'):
        project_cn_set.add(project_cn[0])
    for pjt_cn in project_cn_set:
        platformlist['{}'.format(pjt_cn)] = ProjectInfo.objects.filter(project_cn=pjt_cn)[0].project
        continue
    for i in set(ProjectInfo.objects.values_list('items')):
        items.append(i[0])
    platformlist = sorted(platformlist.items(), key=lambda obj: obj[1], reverse=True)
    items.sort()
    # platformlist = {'摩臣':"mc", '摩臣2':"mc2", '摩登':"md"}
    # items = ['sobet', 'lottery', 'lottery_m', 'sport']
    context = {'platformlist': platformlist, 'items': items, }

    if request.method == "POST":  # 请求方法为POST时，进行处理
        try:
            pst_platform = request.POST.get('id')
            pst_item = request.POST.get('id2')
            myFile = request.FILES.get("myfile", None)  # 获取上传的文件，如果没有文件，则默认为None
            pst_filename = myFile.name
            task_projectinfo = ProjectInfo.objects.get(project=pst_platform, items=pst_item)
            if task_projectinfo.package_name != pst_filename:
                raise FileNotFoundError('Upload file = {}  does not match {}'.format(pst_filename,
                                                                                     task_projectinfo.package_name))
            inputfiledir = os.path.join(task_projectinfo.file_save_base_dir,
                                        datetime.now().strftime('%Y%m%d_%H%M%S'))  # linux run
            # inputfiledir = 'D:\\static' # window debug
            # os.makedirs(inputfiledir)
            fromfile = open(os.path.join(inputfiledir, myFile.name), 'wb+')
            for chunk in myFile.chunks():  # 分块写入文件
                fromfile.write(chunk)
            fromfile.close()

            task = threading.Thread(target=run_tasker, args=(task_projectinfo, inputfiledir))
            task.start()
            messages.success(request, '发布成功！', 'alert-success')
            # if tasker.coversuccess:
            # print('===-======debug  2')
            # coversuccess = True
            # if coversuccess:    #tasker.coversuccess:
            #     messages.success(request, '发布成功！', 'alert-success')
            #     print('===-======debug  3')
            #     RecordOfStatic.objects.filter(items=task_projectinfo).update(isthis_current=False)
            #     record_task = task_projectinfo.recordofstatic_set.create(pub_time=timezone.now(),
            #                                                              deployment_user=request.user.username,
            #                                                              isthis_current=True, return_user='',
            #                                                              upload_file=os.path.join(inputfiledir, myFile.name),
            #                                                              backuplist=', '.join(tasker.backupdir),
            #                                                              newdir=', '.join(tasker.newdirlist),
            #                                                              newfile=', '.join(tasker.newfilelist),
            #                                                              ignore_new=True, )
            #     print('===-======debug  4')
            # else:
            #     messages.error(request, "发布失败，失败原因详见下文", 'alert-danger')
            #     context['task_error'] = 'tasker.errormessage'
            # newfile_len = 1
            # newdir_len = 2
            # if newfile_len > 0 or newdir_len > 0:
            #     messages.warning(request, "默认新增文件不跟新，请联系运维或项目主管审核后更新", 'alert-danger' )
            #     context['newfiles'] = ['static/new/1.txt', '/static/new/mew.image.png'] #'tasker.newfilelist  '
            #     context['newdirs'] = ['static/newimage', 'static/download/']#'tasker.newdirlist'
        except AttributeError as e:  # myFile.name
            messages.error(request, '请选择更新文件', 'alert-danger')
        except FileNotFoundError as e:
            messages.error(request, '上传文件不正确\n{}'.format(str(e)), 'alert-danger')
        except ObjectDoesNotExist as e:
            messages.error(request, '请选择正确的平台-项目对应关系\n{}'.format(str(e)), 'alert-danger')
            print(e)
        except Exception as e:
            print(e)
            messages.error(request, '未知错误： ' + str(e), 'alert-danger')
        finally:
            return render(request, 'frontitems/upload.html', context)
            # return redirect(reverse(upload))
            pass

    elif request.method == 'GET':
        # if request.user.is_authenticated():
        #     #print(request.user.username, '====')
        #     pass
        # return HttpResponse(template.render(context, request))
        context = {'platformlist': platformlist, 'items': items, }
        return render(request, 'frontitems/upload.html', context)
