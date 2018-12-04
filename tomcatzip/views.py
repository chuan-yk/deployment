from django.shortcuts import render
import os
import threading
import os

from django.shortcuts import render, get_object_or_404, redirect, reverse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views import generic
from django_redis import get_redis_connection

from fileupload.models import Fileupload
from .models import RecordOfjavazip
from cmdb.models import ProjectInfo
from cmdb.mytools import file_as_byte_md5sum
from cmdb.remotepubtomcatzip import RemoteZipReplaceWorker

redis_for_app_cli = get_redis_connection("default")


class IndexView(generic.ListView):
    template_name = 'tomcatzip/tomcat_list.html'
    model = Fileupload

    # context_object_name = ''

    def get_queryset(self):
        """Return the type=1 fileload record."""
        return Fileupload.objects.filter(type=2).order_by("-pk", )


@login_required
def list_detail(request, pk):
    """文件详情，发布过程详情"""
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_1_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfjavazip.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
        'pub_filemd5sum': file_as_byte_md5sum(pub_file.file.read())})

    if redis_for_app_cli.exists(pub_lock_key):  # 检查同类型任务发布锁定状态
        pub_lock = {'lock': True, 'pubtask': redis_for_app_cli.hget(pub_lock_key, 'lock_task').decode(),
                    'pub_current_status': redis_for_app_cli.hget(pub_lock_key, 'pub_current_status').decode(),
                    'starttime': redis_for_app_cli.hget(pub_lock_key, 'starttime').decode(),
                    'pub_user': redis_for_app_cli.hget(pub_lock_key, 'pub_user').decode(),
                    }
    else:
        pub_lock = {'lock': False, 'pubtask': None, 'pub_current_status': None, 'starttime': None, 'pub_user': None, }
    try:
        pub_lock['error_detail'] = redis_for_app_cli.hget(record_id, 'error_detail').decode()
    except Exception as e:
        pass
    context = {'pub_file': pub_file, 'pub_lock': pub_lock, 'pub_record': pub_record, 'pjt_info': pjt_info}
    return render(request, 'tomcatzip/tomcat_detail.html', context)


@login_required
def apppub(request, pk):
    """APP 文件发布过程"""
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_4_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfjavazip.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
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
                       '发布任务{0}尚未完成'.format(pub_lock['pubtask'], ), 'alert-danger')

        return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))  # 返回详情页面

    pub_record.pub_status = 1
    pub_record.pub_user = request.user.username
    pub_record.save()
    pub_file.status = 1
    pub_file.pubuser = request.user.username
    pub_file.save()
    print('===   Start  pub {} {} tomcat war, task: {}'.format(pub_file.platform, pub_file.app, record_id))
    pub_task = RemoteZipReplaceWorker(pjt_info.ipaddress, pub_file, pjt_info, pub_record)
    threading_task = threading.Thread(target=pub_task.pip_run, )  # 多线程执行发布过程
    threading_task.start()
    messages.error(request, '提交发布任务成功，任务发布中', 'alert-success')
    return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))


@login_required
def approllback(request, pk):
    pub_file = get_object_or_404(Fileupload, pk=pk)
    pjt_info = get_object_or_404(ProjectInfo, items=pub_file.app, platform=pub_file.platform,
                                 type=pub_file.type)
    record_id = '{0}:{1}:{2}:{3}'.format(pjt_info.platform, pjt_info.items, pub_file.type, pk)  # 唯一任务值mc_apk_4_pk
    pub_lock_key = '{0}:{1}:{2}:lock'.format(pjt_info.platform, pjt_info.items, pub_file.type, )  # 发布锁键值
    pub_record, created = RecordOfjavazip.objects.get_or_create(record_id=record_id, items=pjt_info, defaults={
        'pub_filemd5sum': file_as_byte_md5sum(pub_file.file.read())})
    if redis_for_app_cli.exists(pub_lock_key):  # 检查同类型任务发布锁定状态
        messages.error(request,
                       '当前{0}-{1}发布通道被占用，请稍后重试'.format(pjt_info.platform, pjt_info.items, ),
                       'alert-danger')
        return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))
    if pub_record.pub_status != 2 and pub_file.status != 2:
        messages.error(request,
                       '当前版本发布内容非发布完成状态，请选择正确的回滚版本',
                       'alert-danger')
        return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))
    if pub_record.pub_status != 2 and pub_file.status == 2:
        messages.error(request, '当前版本回滚失败', 'alert-danger')
        return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))

    backup_ver = pub_record.backupsavedir
    pub_task = RemoteZipReplaceWorker(pjt_info.ipaddress, pub_file, pjt_info, pub_record, backup_ver=backup_ver)
    if not pub_task.checkbackdir():
        messages.error(request, '当前版本备份文件不存在，无法回滚', 'alert-danger')
        return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))
    pub_record.pub_status = 4
    pub_record.save()
    threading_task = threading.Thread(target=pub_task.rollback_run(), )  # 多线程执行发布过程
    threading_task.start()
    return redirect(reverse('tmct_url_tag:file_detail', args=[pk, ]))
