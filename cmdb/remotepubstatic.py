#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
import os
import datetime
import tempfile
import shutil
import hashlib
from django_redis import get_redis_connection

from cmdb.models import ProjectInfo
from frontitems.models import RecordOfStatic


# from cachetools import cached, TTLCache  # 1 - let's import the "cached" decorator and the "TTLCache" object from cachetools

def file_as_bytes(file):
    """file read"""
    with file:
        return file.read()


def file_md5sum(filepath):
    """ Usage file_md5sum(file_as_bytes(open(current_file, 'rb')))"""
    return hashlib.md5(file_as_bytes(open(filepath, 'rb'))).hexdigest()


def file_as_byte_md5sum(file_byte):
    return hashlib.md5(file_byte).hexdigest()


from fileupload.models import Fileupload


class RemoteReplaceWorker(object):
    def __init__(self, serverinfo_instance, fileupload_instace, projectinfo_instance, records_instance,
                 shouldbackdir,
                 backup_ver='', ignore_new=True, tmpdir='/tmp'):
        """serverinfo_instance:服务器 ssh 实例
        fileupload_instace: 文件上传行内容
        dstdir:发布目的地址
        fromfile:发布源文件
        platfrom:平台名称
        items:项目名
        backupdir:备份约定目录
        filepk: 上传文件编号
        shouldbackdir: 备份文件夹，如 static/common , static/sobet, sobet
        backup_ver: 备份所在文件夹
        """
        # fileupload_instace = Fileupload.objects.get(pk=4)
        # debug # projectinfo_instance = fileupload_instace.project
        # records_instance = RecordOfStatic.objects.get(pk=2)
        self.remote_server = serverinfo_instance
        self._fileupload_instace = fileupload_instace
        self._projectinfo_instance = projectinfo_instance
        self._records_instance = records_instance
        self._dstdir = projectinfo_instance.dst_file_path  # 发布目标地址
        self._fromfile = fileupload_instace.file.path  # 上传文件
        self._pjtname = projectinfo_instance.platform  # 平台名
        self._items = projectinfo_instance.items  # 项目名
        self._backupdir = projectinfo_instance.backup_file_dir  # 约定平台备份路径，/date/mc
        self._pk = fileupload_instace.pk  # 文件上传编号
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0:
            self._backup_ver = os.path.join(self._backupdir, '{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver  # 约定平台下项目备份路径 /data/mc/[sobet_Ver_日期]
        self.ignore_new = ignore_new  # 忽略新增
        self.redis_cli = get_redis_connection("default")  # redis 客户端
        self.unzipfilelist = []  # 文件夹列表
        self.unzipdirlist = []  # 文件列表
        self.shouldbackdir = shouldbackdir  # 发布文件子目录，对改目录进行备份
        self.backuplist = []  # 备份文件列表
        self.newdir = []  # 新增文件夹
        self.newfile = []  # 新文件
        self.success_status = ''
        self.have_error = False
        self.error_reason = ''
        if tmpdir != '':
            tempfile.tempdir = tmpdir
        else:
            os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
            tempfile.tempdir = os.path.join(os.getcwd(), 'tmp')
        self._tmpdir = tempfile.mkdtemp(prefix=self._items + '_', suffix='_django')
        self.md5dict = {}
        self.pub_type = 0  # 发布类型 0：静态文件
        self.record_id = '{0}:{1}:{2}:{3}'.format(self._pjtname, self._items, self.pub_type, self._pk)
        self._lockkey = '{}:{}:{}:lock'.format(self._pjtname, self._items, self.pub_type)
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()
        # print("debug class init:", self.shouldbackdir)

    def myexecute(self, cmd, stdinstr=''):
        """远程命令执行，检测执行结果"""
        # self.mylogway("执行远程命令: {} , 交互参数 stdin = {}".format(cmd, stdinstr), "Debug")
        self.mylogway("执行远程命令: {} ".format(cmd, stdinstr), "Debug")
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        if stdinstr != '':  # stdin. write in, 有交互过程在此扩展
            pass
        stdout_str = stdout.read().decode().strip()
        stderr_str = stderr.read().decode()
        if stderr_str != '':
            self.mylogway("执行远程命令失败: {} , 交互参数 stdin = {}".format(cmd, stdinstr), level="Error")
            raise IOError(stderr_str)
        return stdout_str

    def mylogway(self, logstr, level="Error"):
        """自定义日志打印"""
        # if level.capitalize() in ["Error", "Info", ]:  # 调整日志级别
        if level.capitalize() in ["Error", "Info", "Debug", ]:  # 调整日志级别
            print("{0}   [{1}]: {2} {3} {4}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level,
                                                    self.remote_server, self.record_id, logstr))

    def checkfiledetail(self):
        """检查文件详情，存redis """
        pub_status = 3  # 约定 3：已完成检查文件详情
        if self.redis_cli.exists(self.record_id):
            # print("Debug: redis 键值 {} 已存在".format(self.record_id))
            tmp_getall = self.redis_cli.hgetall(self.record_id, )
            for rkey, rvalue in tmp_getall.items():
                self.md5dict[rkey.decode()] = rvalue.decode()
            self.cleantmp()
            return self.md5dict

        try:
            self.mylogway("解压文件 {} 到 {} ".format(self._fromfile, self._tmpdir), level='Info')
            shutil.unpack_archive(self._fromfile, extract_dir=self._tmpdir, format='zip')
            if not os.path.isdir(os.path.join(self._tmpdir, '_dist')):
                # print(os.path.isdir(os.path.join(self._tmpdir, '_dist')))
                self.mylogway("解压文件不包含 _dist 文件，请联系开发检查上传文件是否有误！", level='Error')
                raise IOError('could not find _dist dir under tempdir {0}'.format(self._tmpdir))
            # for root, dirs, files in os.walk(os.path.join(self._tmpdir, '_dist/'), topdown=False, followlinks=False):
            for root, dirs, files in os.walk(self._tmpdir, topdown=False, followlinks=False):
                for file in files:
                    current_file = os.path.join(root, file)
                    current_file_name = current_file.split(self._tmpdir)[-1]
                    current_file_md5 = hashlib.md5(file_as_bytes(open(current_file, 'rb'))).hexdigest()
                    # print('----', current_file, current_file_name, os.path.join(root, file).split(self._tmpdir)[-1],
                    #  current_file_md5)
                    self.md5dict[current_file_name] = current_file_md5
                    # print('=== debug, redis hmset', self.record_id, {'{}'.format(current_file_name): current_file_md5})
                    self.redis_cli.hmset(self.record_id, {'{}'.format(current_file_name): current_file_md5})
            else:
                self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        except IOError as e:
            print(e, "dir _dist Does not Exist")
            return {"错误信息": "静态增量文件不包含 '_dist' 目录"}
        except Exception as e1:
            print(e1)
            return {"错误信息2": str(e1)}
        if RecordOfStatic.objects.filter(record_id=self.record_id).count() == 0:
            pub_filemd5sum = file_md5sum(self._fromfile)
            RecordOfStatic(pub_filemd5sum=pub_filemd5sum,
                           items=ProjectInfo.objects.get(items=self._items, platform=self._pjtname, type=self.pub_type),
                           record_id=self.record_id,
                           pub_status=pub_status).save()
        elif RecordOfStatic.objects.get(
                record_id=self.record_id).pub_status == 0:  # RecordOfStatic Exist， pub_status = 0
            RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=pub_status)  # 发布状态更改为3
        self.cleantmp()
        return self.md5dict

    def make_ready(self):
        try:
            self.mylogway("解压文件 {} 到 {} ".format(self._fromfile, self._tmpdir), level='Info')
            shutil.unpack_archive(self._fromfile, extract_dir=self._tmpdir, format='zip')
            if not os.path.isdir(os.path.join(self._tmpdir, '_dist')):
                self.mylogway("解压文件不包含 _dist 文件，请联系开发检查上传文件是否有误！", level='Error')
                raise IOError('could not find _dist dir under tempdir {0}'.format(self._tmpdir))
            for root, dirs, files in os.walk(os.path.join(self._tmpdir, '_dist/'), topdown=False, followlinks=False):
                for dir in dirs:
                    # 类似： '/tmp/xxx/_dist/static/sobet'.split('_dist'), css
                    self.unzipdirlist.append(os.path.join(root.split('_dist/')[1], dir))
                for file in files:
                    self.unzipfilelist.append(os.path.join(root.split('_dist/')[1], file))  #
            # 需备份文件夹
            self.mylogway("解压文件 {} 完成！".format(self._fromfile), level='Info')
            for seconddir in self.unzipdirlist:
                if seconddir.split('/').__len__() < 3 and seconddir != 'static':
                    self.shouldbackdir.add(seconddir)
            print("debug make ready shouldbackdir:", self.shouldbackdir)
            for file in self.unzipfilelist:
                the_redis_key = "{0}:{1}:{2}:file:{3}".format(self._pjtname, self._items, self.pub_type, file)
                if self.redis_cli.hget(the_redis_key, "Exist"):  # redis 文件是否存在
                    continue
                elif self.remote_server.if_exist_file(os.path.join(self._dstdir, file)):  # 远程检查文件是否存在
                    self.redis_cli.hmset(the_redis_key, {"Exist": "True", "Type": 'f'})
                    continue
                else:
                    self.redis_cli.hmset(the_redis_key, {"Type": 'f'})
                    self.newfile.append(file)
            self.mylogway("检测新增文件 : {}！".format(self.newfile), level='Info')
            for the_dir in self.unzipdirlist:
                the_redis_key = "{0}:{1}:{2}:dir:{3}".format(self._pjtname, self._items, self.pub_type, the_dir)
                if self.redis_cli.hget(the_redis_key, "Exist"):  # redis 文件目录是否存在
                    continue
                elif self.remote_server.if_exist_dir(os.path.join(self._dstdir, the_dir)):  # 远程检查目录是否存在
                    self.redis_cli.hmset(the_redis_key, {"Exist": "True", "Type": 'd'})
                    continue
                else:
                    self.redis_cli.hmset(the_redis_key, {"Type": 'd'})
                    self.newdir.append(the_dir)
            self.mylogway("检测新增文件夹 : {}！".format(self.newdir), level='Info')
        except Exception as e1:
            self.have_error = True
            self.mylogway("解压文件异常，错误详情 : {}".format(e1), level='Error')
        finally:
            self.success_status = 'unziped_success'

    def do_backup(self):
        self.ssh = self.remote_server.get_sshclient()
        for i in self.shouldbackdir:
            if i in self.newdir:  # 新增static/commom 同级别文件夹，跳过备份过程
                self.mylogway('新增文件夹！new  dir  {} ignore back step ， continue...'.format(i), level='Info')
                continue
            try:
                backupdir = os.path.join(self._backup_ver, i)  # 备份完整路径 /xxx/xx/项目/project_201YddHHMMSS/static/lottery
                self.myexecute("mkdir -p {}".format(backupdir))
                self.myexecute("/bin/cp -r {0}/*  {1}/".format(os.path.join(self._dstdir, i), backupdir))
                self.backuplist.append(backupdir)
            except Exception as e:
                self.myexecute("备份静态文件出错，错误详情{}".format(e))
                self.success_status = 'backup_fail'
                self.have_error = True
        else:
            if not self.have_error:
                self.success_status = 'backup_success'

    def do_cover(self):
        """
        :param: self.ignore_new, 忽略新增
        :return:
        """
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()
        try:
            if self.ignore_new:
                """"创建新建文件夹"""
                for ndir in self.newdir:
                    abspath_path = os.path.join(self._dstdir, ndir)
                    self.myexecute("mkdir -p '{}'".format(abspath_path))
            for pub_file in self.unzipfilelist:
                # ignore == False, 不覆盖新增文件
                if not self.ignore_new and pub_file in self.newfile:
                    continue
                self.mylogway('sftp put {} {}'.format(os.path.join(self._tmpdir, '_dist', pub_file),
                                                      os.path.join(self._dstdir, pub_file)), level='Debug')
                self.sftp.put(os.path.join(self._tmpdir, '_dist', pub_file), os.path.join(self._dstdir, pub_file))
        except FileNotFoundError as e:  # 捕获xftp put 过程目的文件夹不存在的异常
            self.mylogway('Sftp put file error {}'.format(e), level='Error')
            self.have_error = True
            self.rollback(onpub=True)
            self.error_reason = 'scp {} {} Sftp put file error: {}'.format(
                os.path.join(self._tmpdir, '_dist', pub_file), os.path.join(self._dstdir, pub_file), e)

        except Exception as e:
            self.mylogway("Unknown Exception as: {}".format(e), level='Error')
            self.have_error = True
            self.rollback(onpub=True)
        if not self.have_error:
            self.remote_server.sshclient_close()
            self.remote_server.xftpclient_close()
            self.success_status = 'pub_success'
            self.mylogway("{} 发布完成！".format(self._fromfile), level='Info')

    def checkbackdir(self):
        """检查备份文件是否存在"""
        if len(self.shouldbackdir) == 0:
            return False
        for tdir in self.shouldbackdir:
            if not self.remote_server.if_exist_dir(os.path.join(self._backup_ver, tdir)):
                return False
        else:
            return True

    def rollback(self, onpub=False):
        """
        :param: onpub 正常发布状态， 出现失败回滚
        :return:
        """
        self.ssh = self.remote_server.get_sshclient()
        if onpub:
            self.success_status = 'pub_fail'
        else:
            self.success_status = "roll_back_Start"
            self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                                 'pub_user': self._records_instance.pub_user,
                                                 'pub_current_status': self.success_status,
                                                 })  # 回滚过程加锁
        roll_back_dir = os.path.join(self._backup_ver, 'roll_back')
        try:
            for tdir in self.shouldbackdir:  # 还原过程, 先mv, 再还原
                roll_back_dir_add = os.path.join(roll_back_dir, tdir)
                self.myexecute('mkdir -p {}'.format(roll_back_dir_add))
                self.myexecute("mv {}/* {}".format(os.path.join(self._dstdir, tdir), roll_back_dir_add))
                self.myexecute(
                    "mv {}/* {}".format(os.path.join(self._backup_ver, tdir), os.path.join(self._dstdir, tdir)))

                self.mylogway("debug Function rollback: mv {}/* {}".format(os.path.join(self._backup_ver, tdir),
                                                                os.path.join(self._dstdir, tdir)), level="Info")

            if not onpub:  # 直接调用回滚操作
                self.redis_cli.delete(self._lockkey)  # 回滚完成，释放发布lock
                RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(backuplist='', pub_status=5, )
                Fileupload.objects.filter(type=self._fileupload_instace.type,
                                          pk__gte=self._fileupload_instace.pk,
                                          project_id=self._fileupload_instace.project_id,
                                          ).update(status=0, pubuser='')  # 更改回滚影响文件的发布状态
                self.cleantmp()

        except IOError as e3:
            self.mylogway("Unknown Exception as: {}".format(e3), level='Error')
            self.mylogway('Debug there, rollback dir {}'.format(roll_back_dir), level='Error')
            self.redis_cli.delete(self._lockkey)  # 回滚失败，任务结束，释放锁
            self.error_reason = str(e3)
            if not onpub:
                self.redis_cli.hmset(self.record_id,
                                     {'error_detail': str(self.success_status) + '  ' + self.error_reason})
                RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=-2, )  # 回滚失败， -2

        self.remote_server.sshclient_close()
        self.remote_server.xftpclient_close()

    def cleantmp(self):
        shutil.rmtree(self._tmpdir)

    def pip_run(self):
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self._records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=1, )  # 修改发布状态
        Fileupload.objects.filter(pk=self._fileupload_instace.pk).update(status=1, )  # 修改发布状态
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'check original file '})  # 发布过程更新状态
        if not self.have_error:
            self.make_ready()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})  # 发布过程更新状态
        if not self.have_error:
            self.do_backup()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.do_cover()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        self.redis_cli.delete(self._lockkey)
        self.cleantmp()
        RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(
            backuplist=', '.join(self.shouldbackdir),
            newdir=', '.join(self.newdir),
            newfile=', '.join(self.newfile),
            ignore_new=self.ignore_new,
            backupsavedir=self._backup_ver, )  # 更新records 记录
        self._records_instance.refresh_from_db()  # 重新读取数据库值
        if self.have_error:
            RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=-1, )  # 修改发布状态
            Fileupload.objects.filter(pk=self._fileupload_instace.pk).update(status=-1, )  # 修改发布状态
            self.redis_cli.hmset(self.record_id, {'error_detail': self.success_status + ': ' + self.error_reason})
            self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        else:
            RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=2, )  # 修改发布状态
            Fileupload.objects.filter(pk=self._fileupload_instace.pk).update(status=2, )  # 修改发布状态

        # return {"Error": self.have_error, "status": self.success_status, "backup_ver": self._backup_ver,
        #         "backed_up_dir": self.shouldbackdir, "pub_ignore_new": self.ignore_new, "add_file": self.newfile,
        #         "add_dir": self.newdir, "update_file_list": self.unzipfilelist, }

    def test_run(self):
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self._records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=1, )  # 修改发布状态
        Fileupload.objects.filter(pk=self._fileupload_instace.pk).update(status=1, )  # 修改发布状态
        print('start_run')
        import time
        time.sleep(3)
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'hahah1'})
        print('debug test_run', 'hahah1')
        time.sleep(3)
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'hahah222222222'})
        print('debug test_run', 'hahah2')
        time.sleep(3)
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'hahah3333333333333333333'})
        print('debug test_run', 'hahah3333333333333333333')
        self._records_instance.backuplist = ', '.join(self.shouldbackdir)  # 不带备份路径
        self._records_instance.newdir = ', '.join(self.newdir)
        self._records_instance.newfile = ', '.join(self.newfile)
        RecordOfStatic.objects.filter(pk=self._records_instance.pk).update(pub_status=2, )  # 修改发布状态
        Fileupload.objects.filter(pk=self._fileupload_instace.pk).update(status=2, )  # 修改发布状态
        print('================, change fileupload_instace.status = 2 ', self._fileupload_instace.pk)
        self.redis_cli.delete(self._lockkey)
        # self.redis_cli.hmset(self.record_id, {'error_detail': self.success_status})   # redis: record_id: error_detail
        # self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        self.cleantmp()
        print('end_test run ')

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
