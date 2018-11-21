import os
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
import threading
import time
from datetime import datetime, date, timedelta
from django.core.exceptions import ObjectDoesNotExist
from django_redis import get_redis_connection
from fileupload.models import Fileupload
from frontitems.models import RecordOfStatic
from cmdb.models import ServerInfo, ProjectInfo
from .remotepubstatic import RemoteReplaceWorker, file_as_byte_md5sum


@login_required
def list(request):
    """静态文件全部内容列表
       Fileupload: 0 为静态文件
    """
    static_uploadfile_list = Fileupload.objects.filter(type=0).order_by('-id', '-create_date')
    return render(request, 'frontitems/list.html', {'static_uploadfile_list': static_uploadfile_list})


@login_required
def list_detail(request, pk):
    """指定pk 文件详情, Get参数 ?filemd5=1: 显示更新文件MD5 信息，"""
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,  # 唯一任务值
                                 type=pub_file.type)
    record_id = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', pk)

    if RecordOfStatic.objects.filter(record_id=record_id).count() == 0:  # 初始化插入 Record 记录
        uploadfile_md5 = file_as_byte_md5sum(pub_file.file.read())  # 上传文件Md5
        RecordOfStatic(pub_filemd5sum=uploadfile_md5,
                       items=ProjectInfo.objects.get(items=pjt_info.items, platform=pjt_info.platform, type=0),
                       record_id=record_id,
                       pub_status=0  # 初始状态
                       ).save()
    else:
        uploadfile_md5 = RecordOfStatic.objects.get(record_id=record_id).pub_filemd5sum  # 已存在记录直接从数据库查
    if request.GET.get('filemd5') == '1':
        show = True
        pub_task = RemoteReplaceWorker(pjt_info.ipaddress,
                                       pub_file,
                                       pjt_info,
                                       RecordOfStatic.objects.get(record_id=record_id),
                                       tmpdir='media',
                                       )
        MD5 = pub_task.checkfiledetail()
        try:
            MD5.pop('error_detail')
        except Exception as e:
            pass
    else:
        show = False
        MD5 = {'None': None}

    uploadfile_detail = pub_file  # 兼顾模板写法，不同名同内容变量
    # pub_lock 发布锁状态获取
    redis_for_detail_cli = get_redis_connection("default")
    pub_lock_key = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', 'lock')
    if redis_for_detail_cli.exists(pub_lock_key):  # 发布占用锁定状态,
        pub_lock = {'lock': True, 'pubtask': redis_for_detail_cli.hget(pub_lock_key, 'lock_task').decode(),
                    'pub_current_status': redis_for_detail_cli.hget(pub_lock_key, 'pub_current_status').decode(),
                    'starttime': redis_for_detail_cli.hget(pub_lock_key, 'starttime').decode(),
                    'pub_user': redis_for_detail_cli.hget(pub_lock_key, 'pub_user').decode(),
                    }

    elif pub_file.status != 0:  # 锁定状态
        pub_lock = {'lock': True, 'pubtask': None, 'pub_current_status': None, 'starttime': None, 'pub_user': None, }
    else:
        pub_lock = {'lock': False, 'pubtask': None, 'pub_current_status': None, 'starttime': None, 'pub_user': None, }
    filemd5 = {'show': show, 'MD5': MD5}
    context = {'uploadfile_detail': uploadfile_detail,
               'pub_lock': pub_lock,
               'filemd5': filemd5,
               "uploadfile_md5": uploadfile_md5, }

    return render(request, 'frontitems/file_detail.html', context)


@login_required
def pub(request, pk):
    redis_for_pub_cli = get_redis_connection("default")
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    pub_lock_key = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', 'lock')  # 发布任务锁
    record_id = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', pk)  # 唯一任务值
    pub_user = request.user.username
    if RecordOfStatic.objects.filter(record_id=record_id).count() == 0:  # 初始化插入 Record 记录
        uploadfile_md5 = file_as_byte_md5sum(pub_file.file.read())  # 上传文件Md5
        RecordOfStatic(pub_filemd5sum=uploadfile_md5,
                       items=ProjectInfo.objects.get(items=pjt_info.items, platform=pjt_info.platform, type=0),
                       pub_user=pub_user,
                       record_id=record_id,
                       pub_status=0  # 初始状态
                       ).save()

    if redis_for_pub_cli.exists(pub_lock_key):  # 发布锁定状态，返回占用提示
        lock_task = redis_for_pub_cli.hget(pub_lock_key, 'lock_task').decode()
        messages.error(request,
                       '当前{0}-{1}发布通道被占用，请稍后重试'.format(pjt_info.platform, pjt_info.items, ),
                       'alert-danger')
        messages.error(request,
                       '发布任务{0}尚未完成'.format(lock_task), 'alert-danger')
        static_uploadfile_list = Fileupload.objects.filter(type=0)

        return render(request, 'frontitems/list.html', {'static_uploadfile_list': static_uploadfile_list})  # 返回默认发布页面

    pub_record = RecordOfStatic.objects.get(record_id=record_id, )
    RecordOfStatic.objects.filter(pk=pub_record.pk).update(pub_user=request.user.username)  # 更新Records 表 pub_user 字段
    Fileupload.objects.filter(pk=pub_file.pk).update(pubuser=request.user.username)  # 更新fileupload 表 pubuser 字段

    pub_task = RemoteReplaceWorker(pjt_info.ipaddress,
                                   pub_file,
                                   pjt_info,
                                   pub_record,
                                   tmpdir='media',  # 解压临时文件，跟进环境调整
                                   )
    threading_task = threading.Thread(target=pub_task.pip_run, )  # 正式使用
    # threading_task = threading.Thread(target=pub_task.test_run, )  # windows 开发过程调试
    threading_task.start()
    # time.sleep(0.01)  # sleep while wait for insert key to redis
    return redirect(reverse('frontitems:pub_detail', args=[pk, ]))


@login_required
def pubresult(request, pk):
    redis_for_pub_cli = get_redis_connection("default")
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    pub_lock_key = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', 'lock')  # 发布任务锁
    record_id = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', pk)  # 唯一任务值
    try:
        redis_detail = {'lock_task': redis_for_pub_cli.hget(pub_lock_key, 'lock_task').decode(),
                        'pub_current_status': redis_for_pub_cli.hget(pub_lock_key, 'pub_current_status').decode(),
                        'starttime': redis_for_pub_cli.hget(pub_lock_key, 'starttime').decode(),
                        'pub_user': redis_for_pub_cli.hget(pub_lock_key, 'pub_user').decode(),
                        'error_detail': None
                        }
        pub_record = RecordOfStatic.objects.get(record_id=record_id, )
    except AttributeError:
        print('Info Function pubresult, Try get redis task lock value get None ')
        redis_detail = {'lock_task': None,
                        'pub_current_status': None,
                        'starttime': None,
                        'pub_user': None,
                        }
        pub_record = RecordOfStatic.objects.get(record_id=record_id, )  # 捕获redis lock 状态后再读取 Records 表内容
        if pub_record.pub_status == -1:
            redis_detail = {'error_detail': redis_for_pub_cli.hget(record_id, 'error_detail').decode(), }

        elif pub_record.pub_status == 1:
            redis_detail = {'error_detail': '未成功捕获异常，请联系dendi<dendi@networkws.com> 排查', }
    if pub_record.pub_status == 0:
        messages.error(request,
                       '该任务未进行发布操作！', 'alert-danger')
        static_uploadfile_list = Fileupload.objects.filter(type=0)
        return render(request, 'frontitems/list.html', {'static_uploadfile_list': static_uploadfile_list})  # 返回默认发布页面
    newfilelist = pub_record.newfile.split(',')
    newdirlist = pub_record.newdir.split(',')
    context = {'pub_file': pub_file, 'pub_record': pub_record, 'redis_detail': redis_detail, 'newfilelist': newfilelist,
               'newdirlist': newdirlist}
    return render(request, 'frontitems/pub_detail.html', context)


def pubreturn(request, pk):
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)

    record_id = '{0}_{1}_{2}_{3}'.format(pjt_info.platform, pjt_info.items, '0', pk)  # 唯一任务值
    pub_record = get_object_or_404(RecordOfStatic, record_id=record_id, )
    if pub_record.pub_status != 2 or len(pub_record.backuplist) == 0 or len(pub_record.backupsavedir) == 0:
        messages.error(request,
                       '当前版本发布内容非发布完成状态，请选择正确的回滚版本',
                       'alert-danger')
        return redirect(reverse('frontitems:file_detail', args=[pk, ]))

    shouldbackdir = set([i.strip() for i in pub_record.backuplist.split(',')])
    backup_ver = pub_record.backupsavedir
    pub_task = RemoteReplaceWorker(pjt_info.ipaddress,
                                   pub_file,
                                   pjt_info,
                                   pub_record,
                                   shouldbackdir=shouldbackdir,
                                   backup_ver=backup_ver,
                                   tmpdir='media',  # 解压临时文件，跟进环境调整
                                   )
    if not pub_task.checkbackdir():
        messages.error(request,
                       '当前版本备份文件不完整，无法回滚',
                       'alert-danger')
        return redirect(reverse('frontitems:pub_detail', args=[pk, ]))  # 返回详情页面 错误信息
    RecordOfStatic.objects.filter(pk=pub_record.pk).update(return_user=request.user.username)  # 更新 return_user
    pub_record.pub_status = 4                                      # 更改状态为发布中
    pub_record.save()
    pub_record.refresh_from_db()
    threading_task = threading.Thread(target=pub_task.rollback, )  # 另起线程调用， 异步执行
    threading_task.start()
    return redirect(reverse('frontitems:pub_detail', args=[pk, ]))
