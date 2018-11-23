from django.shortcuts import render
import os
import threading

from django.shortcuts import render, get_object_or_404, redirect, reverse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django_redis import get_redis_connection

from fileupload.models import Fileupload
from .models import RecordOfApp
from cmdb.models import ProjectInfo
from cmdb.mytools import file_as_byte_md5sum
from cmdb.remotepubapp import RemoteAppReplaceWorker

redis_for_app_cli = get_redis_connection("default")


@login_required
def list_app(request):
    """静态文件全部内容列表
       Fileupload: 4 为APP文件
    """
    pub_file_list = Fileupload.objects.filter(type=4).order_by('-id', '-create_date')
    return render(request, 'frontapp/list.html', {'pub_file_list': pub_file_list})


@login_required
def list_detail(request, pk):
    """文件详情"""
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_4_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfApp.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
        'pub_filemd5sum': file_as_byte_md5sum(pub_file.file.read())})
    if not created:
        pub_record.pub_filemd5sum = file_as_byte_md5sum(pub_file.file.read())
        pub_record.save()

    if redis_for_app_cli.exists(pub_lock_key):  # 检查同类型任务发布锁定状态
        pub_lock = {'lock': True, 'pubtask': redis_for_app_cli.hget(pub_lock_key, 'lock_task').decode(),
                    'pub_current_status': redis_for_app_cli.hget(pub_lock_key, 'pub_current_status').decode(),
                    'starttime': redis_for_app_cli.hget(pub_lock_key, 'starttime').decode(),
                    'pub_user': redis_for_app_cli.hget(pub_lock_key, 'pub_user').decode(),
                    }
    else:
        pub_lock = {'lock': False, 'pubtask': None, 'pub_current_status': None, 'starttime': None, 'pub_user': None, }
    context = {'pub_file': pub_file, 'pub_lock': pub_lock, 'pub_record': pub_record, 'pjt_info': pjt_info}
    return render(request, 'frontapp/list_detail.html', context)


@login_required
def apppub(request, pk):
    """APP 文件发布过程"""
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_4_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfApp.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
        'pub_filemd5sum': file_as_byte_md5sum(pub_file.file.read())})
    if redis_for_app_cli.exists(pub_lock_key):  # 检查同类型任务发布锁定状态
        pub_lock = {'lock': True, 'pubtask': redis_for_app_cli.hget(pub_lock_key, 'lock_task').decode(),
                    'pub_current_status': redis_for_app_cli.hget(pub_lock_key, 'pub_current_status').decode(),
                    'starttime': redis_for_app_cli.hget(pub_lock_key, 'starttime').decode(),
                    'pub_user': redis_for_app_cli.hget(pub_lock_key, 'pub_user').decode(),
                    }
        messages.error(request,
                       '当前{0}-{1}发布通道被占用，请稍后重试'.format(pjt_info.platform, pjt_info.items, ),
                       'alert-danger')
        messages.error(request,
                       '发布任务{0}尚未完成'.format(pub_lock['lock_task'], ), 'alert-danger')
        pub_file_list = Fileupload.objects.filter(type=4).order_by('-id', '-create_date')
        return render(request, 'frontapp/list_detail.html', {'pub_file_list': pub_file_list})  # 返回默认发布页面

    pub_record.pub_status = 1
    pub_record.pub_user = request.user.username
    pub_record.save()
    pub_file.status = 1
    pub_file.pubuser = request.user.username
    pub_file.save()
    print('Start pub {} {}'.format(pub_file.platform, pub_file.app))
    pub_task = RemoteAppReplaceWorker(pjt_info.ipaddress, pub_file, pjt_info, pub_record)
    threading_task = threading.Thread(target=pub_task.pip_run, )        # 多线程执行发布过程
    threading_task.start()
    return redirect(reverse('frontapp:file_detail', args=[pk, ]))


@login_required
def approllback(request, pk):
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_4_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfApp.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
        'pub_filemd5sum': file_as_byte_md5sum(pub_file.file.read())})

    if pub_record.pub_status != 2:
        messages.error(request,
                       '当前版本发布内容非发布完成状态，请选择正确的回滚版本',
                       'alert-danger')
        return redirect(reverse('frontapp:file_detail', args=[pk, ]))
    if redis_for_app_cli.exists(pub_lock_key):  # 检查同类型任务发布锁定状态
        messages.error(request,
                       '当前{0}-{1}发布通道被占用，请稍后重试'.format(pjt_info.platform, pjt_info.items, ),
                       'alert-danger')
        return redirect(reverse('frontapp:file_detail', args=[pk, ]))
    backup_ver = pub_record.backup_file
    pub_record.pub_status = 4
    pub_record.save()
    pub_task = RemoteAppReplaceWorker(pjt_info.ipaddress, pub_file, pjt_info, pub_record, backup_ver=backup_ver)
    threading_task = threading.Thread(target=pub_task.rollback(), )  # 多线程执行发布过程
    threading_task.start()
    return redirect(reverse('frontapp:file_detail', args=[pk, ]))