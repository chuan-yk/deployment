#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
"""APP 文件发布"""
import os
import datetime
import shutil
from django_redis import get_redis_connection

from cmdb.models import ProjectInfo
from frontapp.models import RecordOfApp
from fileupload.models import Fileupload


class RemoteAppReplaceWorker(object):
    def __init__(self, serverinfo_instance, fileupload_instace, projectinfo_instance, records_instance, backup_ver=''):
        """serverinfo_instance:服务器 ssh 实例
        fileupload_instace: 文件上传行内容
        records_instance:   发布记录数据行内容
        backup_ver: 备份所在文件夹
        """
        # debug # fileupload_instace = Fileupload.objects.get(pk=8)  # debug
        # debug # projectinfo_instance = fileupload_instace.project
        # records_instance = RecordOfApp.objects.get(pk=2)
        self.remote_server = serverinfo_instance
        self.fileupload_instace = fileupload_instace
        self.projectinfo_instance = projectinfo_instance
        self.records_instance = records_instance
        self._dstdir = projectinfo_instance.dst_file_path  # 发布目标地址
        self._dstfile = os.path.join(self._dstdir, self.fileupload_instace.slug)
        self._fromfile = fileupload_instace.file.path  # 上传文件路径
        self._pjtname = projectinfo_instance.platform  # 平台名
        self._items = projectinfo_instance.items  # 项目名
        self._backupdir = projectinfo_instance.backup_file_dir  # 约定平台备份路径，/date/mc
        self._pk = fileupload_instace.pk  # 文件上传编号
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0:
            self._backup_ver = os.path.join(self._backupdir, '{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver  # 约定平台下项目备份路径 /data/mc/[sobet_Ver_日期]
        self.redis_cli = get_redis_connection("default")  # redis 客户端
        self.success_status = ''
        self.have_error = False
        self.error_reason = ''
        self.pub_type = fileupload_instace.type  # 发布类型 0：静态文件
        self.record_id = records_instance.record_id  # 发布任务ID
        self._lockkey = '{}:{}:{}:lock'.format(self._pjtname, self._items, self.pub_type)
        self.ssh = None
        self.sftp = None

    def do_backup(self):
        self.ssh = self.remote_server.get_sshclient()
        try:
            stdin, stdout, stderr = self.ssh.exec_command("mkdir -p {}".format(self._backup_ver))
            stderr_txt = stderr.read().decode()
            if len(stderr_txt) > 0:
                self.have_error = True
                raise IOError('backup Function mkdir dir {} fail, Error: {}'.format(self._backup_ver, stderr_txt))
            stdin, stdout, stderr = self.ssh.exec_command("/bin/cp {} {}".format(self._dstfile, self._backup_ver))
            stderr_txt = stderr.read().decode()
            if len(stderr_txt) and (
                    self.projectinfo_instance.items == 'apk' or self.projectinfo_instance.items == 'ipa') > 0:
                raise IOError('backup Function: backup file {} fail, Error: {}'.format(self._dstfile, stderr_txt))
        except Exception as e:
            print('Error: ', e)
            self.have_error = True
            self.error_reason = 'back file {} fail, Error: {}'.format(self._dstfile, e)
        finally:
            if self.have_error:
                self.success_status = 'backup_fail'
            else:
                self.success_status = 'backup_success'

    def do_cover(self):
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()
        try:
            stdin, stdout, stderr = self.sftp.put(self._fromfile, self._dstfile)
            stderr_txt = stderr.read().decode()
            if len(stderr_txt) > 0:
                self.have_error = True
                raise IOError("""RemoteAppReplaceWorker do_cover Function scp  {}  {} fail, 
                                Error: {}""".format(self._fromfile, self._dstfile, stderr_txt))
        except FileNotFoundError as e:  # 捕获xftp put 过程目的文件夹不存在的异常
            print('Sftp put file error', e)
            self.have_error = True
            self.error_reason = 'upload file  {} not Exist'.format(self._fromfile)
        except Exception as e:
            print("Unknown Exception as:", e)
            self.have_error = True
            self.error_reason = """RemoteAppReplaceWorker do_cover Function scp  {}  {} fail, 
                                Error: {}""".format(self._fromfile, self._dstfile, e)
        if not self.have_error:
            self.remote_server.sshclient_close()
            self.remote_server.xftpclient_close()
            self.success_status = 'pub_success'
            print("{} 发布完成！".format(self._fromfile))

    def checkbackdir(self):
        """检查备份文件是否存在"""
        self.ssh = self.remote_server.get_sshclient()
        if self.remote_server.if_exist_file(os.path.join(self._backup_ver, self.fileupload_instace.slug)):
            return True
        else:
            return False

    def rollback(self):
        """
        :param: onpub 正常发布状态， 出现失败回滚
        :return:
        """
        self.ssh = self.remote_server.get_sshclient()
        self.success_status = "roll_back_Start"
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': self.success_status,
                                             })  # 回滚过程加锁
        stdin, stdout, stderr = self.ssh.exec_command(
            "/bin/cp {} {}".format(os.path.join(self._backup_ver, self.fileupload_instace.slug), self._dstfile))
        stderr_txt = stderr.read().decode()
        if len(stderr_txt) > 0:
            self.have_error = True
            self.error_reason = ("Error /bin/cp {} {}".format(
                os.path.join(self._backup_ver, self.fileupload_instace.slug),
                self._dstfile))
            self.redis_cli.hmset(self.record_id, {'error_detail': self.error_reason})
            self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
            RecordOfApp.objects.filter(pk=self.records_instance.pk).update(pub_status=-2, )  # 修改发布状态,回滚失败

        else:
            RecordOfApp.objects.filter(pk=self.records_instance.pk).update(pub_status=5,)   # 修改发布状态,回滚完成
            Fileupload.objects.filter(pk=self.fileupload_instace.pk, ).update(status=0,)  # 更改回滚影响文件的发布状态
        self.redis_cli.delete(self._lockkey)
        self.remote_server.sshclient_close()
        self.remote_server.xftpclient_close()

    def pip_run(self):
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        RecordOfApp.objects.filter(pk=self.records_instance.pk).update(pub_status=1, )  # 修改发布状态
        Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=1, )  # 修改发布状态
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'check original file '})  # 发布过程更新状态
        if not self.have_error:
            self.do_backup()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.do_cover()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        self.redis_cli.delete(self._lockkey)

        RecordOfApp.objects.filter(pk=self.records_instance.pk).update(
            backup_file=self._dstfile)  # 更新records 记录, 存入备份文件路径信息
        self.records_instance.refresh_from_db()  # 重新读取数据库值
        if self.have_error:
            RecordOfApp.objects.filter(pk=self.records_instance.pk).update(pub_status=-1, )  # 修改发布状态 ，发布失败
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=-1, )  # 修改发布状态， 发布失败
            self.redis_cli.hmset(self.record_id, {'error_detail': self.success_status + ': ' + self.error_reason})
            self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        else:
            RecordOfApp.objects.filter(pk=self.records_instance.pk).update(pub_status=2, )  # 修改发布状态，发布完成
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=2, )  # 修改发布状态，发布完成

# cache = TTLCache(maxsize=100, ttl=365*24*60*60)
# @cached(cache)
# def lock_status(platfrom, items):
#     import threading
#     return threading.Lock()
# pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
# r = redis.Redis(connection_pool=pool)
# r.hset("hash1", "k1", "v1")
# r.hset("hash1", "k2", "v2")
# print(r.hkeys("hash1")) # 取hash中所有的key
# print(r.hget("hash1", "k1"))    # 单个取hash的key对应的值
# print(r.hmget("hash1", "k1", "k2")) # 多个取hash的key对应的值
# r.hsetnx("hash1", "k2", "v3") # 只能新建
# r.hexists("hash1", "k4")  # False 不存在 # 存在
# r.expire("list5", time=3) # 超时时间
