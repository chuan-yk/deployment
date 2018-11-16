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
fileupload_instace = Fileupload.objects.get(pk=9)

class RemoteReplaceWorker(object):
    def __init__(self, serverinfo_instance, fileupload_instace, projectinfo_instance, dstdir, fromfile, platfrom, items, backupdir, filepk, shouldbackdir=set(),
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
        fileupload_instace = Fileupload.objects.get(pk=9)
        projectinfo_instance = Fileupload.
        self._remote_server = serverinfo_instance
        self._dstdir = dstdir
        self._fromfile = fromfile
        self._pjtname = platfrom
        self._items = items
        self._backupdir = backupdir  # /date/release
        self._pk = filepk
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0:
            self._backup_ver = os.path.join(self._backupdir, '{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver
        self.ignore_new = ignore_new
        self.redis_cli = get_redis_connection("default")
        self.unzipfilelist = []  # 文件夹列表
        self.unzipdirlist = []  # 文件列表
        self.shouldbackdir = shouldbackdir  # 发布文件子目录，对改目录进行备份
        self.backuplist = []  # 备份文件列表
        self.newdir = []  # 新增文件夹
        self.newfile = []  # 新文件
        self.success_status = ''
        self.have_error = False
        if tmpdir != '':
            tempfile.tempdir = tmpdir
        else:
            os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
            tempfile.tempdir = os.path.join(os.getcwd(), 'tmp')
        self._tmpdir = tempfile.mkdtemp(prefix=items + '_', suffix='_django')
        self.md5dict = {}
        self.pub_type = 0   # 发布类型 0：静态文件
        self.ssh = None
        self.sftp = None

    def checkfiledetail(self):
        """检查文件详情，存redis """
        pub_status = 3  # 约定 3：已完成检查文件详情
        record_id = '{0}_{1}_{2}_{3}'.format(self._pjtname, self._items, self.pub_type, self._pk)
        if self.redis_cli.exists(record_id):
            # print("Debug: redis 键值 {} 已存在".format(record_id))
            tmp_getall = self.redis_cli.hgetall(record_id, )
            for rkey, rvalue in tmp_getall.items():
                self.md5dict[rkey.decode()] = rvalue.decode()
            self.cleantmp()
            return self.md5dict

        try:
            shutil.unpack_archive(self._fromfile, extract_dir=self._tmpdir, format='zip')
            if not os.path.isdir(os.path.join(self._tmpdir, '_dist')):
                # print(os.path.isdir(os.path.join(self._tmpdir, '_dist')))
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
                    # print('=== debug, redis hmset', record_id, {'{}'.format(current_file_name): current_file_md5})
                    self.redis_cli.hmset(record_id, {'{}'.format(current_file_name): current_file_md5})
            else:
                self.redis_cli.expire(record_id, 60*60*24*14)
        except IOError as e:
            print(e, "dir _dist Does not Exist")
            return {"错误信息": "静态增量文件不包含 '_dist' 目录"}
        except Exception as e1:
            print(e1)
            return {"错误信息2": str(e1)}
        if RecordOfStatic.objects.filter(record_id=record_id).count() == 0:
            pub_filemd5sum = file_md5sum(self._fromfile)
            RecordOfStatic(pub_filemd5sum=pub_filemd5sum,
                           items=ProjectInfo.objects.get(items=self._items, platform=self._pjtname, type=self.pub_type),
                           record_id=record_id,
                           pub_status=pub_status).save()
        elif RecordOfStatic.objects.get(record_id=record_id).pub_status == 0 :  # RecordOfStatic Exist， pub_status = 0
            record_line_info  = RecordOfStatic.objects.get(record_id=record_id)
            record_line_info.pub_status = pub_status
            record_line_info.save()
        self.cleantmp()
        return self.md5dict

    def make_ready(self):
        try:
            shutil.unpack_archive(self._fromfile, extract_dir=self._tmpdir, format='zip')
            if not os.path.isdir(os.path.join(self._tmpdir, '_dist')):
                raise IOError('could not find _dist dir under tempdir {0}'.format(self._tmpdir))
            for root, dirs, files in os.walk(os.path.join(self._tmpdir, '_dist/'), topdown=False, followlinks=False):
                for dir in dirs:
                    # 类似： '/tmp/xxx/_dist/static/sobet'.split('_dist'), css
                    self.unzipdirlist.append(os.path.join(root.split('_dist/')[1], dir))
                for file in files:
                    self.unzipfilelist.append(os.path.join(root.split('_dist/')[1], file))  #
            # 需备份文件夹
            for seconddir in self.unzipdirlist:
                if seconddir.split('/').__len__() < 3 and seconddir != 'static':
                    self.shouldbackdir.add(seconddir)
            for file in self.unzipfilelist:
                if self.redis_cli.hget("{0}:{1}:{2}".format(self._pjtname, self._items, file), "Exist"):
                    continue
                elif self._remote_server.if_exist_file(os.path.join(self._dstdir, file)):
                    self.redis_cli.hmset("{0}:{1}:{2}".format(self._pjtname, self._items, file),
                                         {"Exist": True, "Type": 'f'})
                    continue
                else:
                    self.redis_cli.hmset("{0}:{1}:{2}".format(self._pjtname, self._items, file),
                                         {"Type": 'f'})
                    self.newfile.append(file)
            for the_dir in self.unzipdirlist:
                if self.redis_cli.hget("{0}:{1}:{2}".format(self._pjtname, self._items, the_dir), "Exist"):
                    continue
                elif self._remote_server.if_exist_dir(os.path.join(self._dstdir, the_dir)):
                    self.redis_cli.hmset("{0}:{1}:{2}".format(self._pjtname, self._items, the_dir),
                                         {"Exist": True, "Type": 'd'})
                    continue
                else:
                    self.redis_cli.hmset("{0}:{1}:{2}".format(self._pjtname, self._items, the_dir),
                                         {"Type": 'd'})
                    self.newdir.append(the_dir)
        except Exception as e1:
            self.have_error = True
            print('Error e1:', e1)
        finally:
            self.success_status = 'unziped_success'

    def do_backup(self):
        self.ssh = self._remote_server.get_sshclient()
        for i in self.shouldbackdir:
            try:
                backupdir = os.path.join(self._backup_ver, i)  # 备份完整路径 /xxx/xx/项目/project_201YddHHMMSS/
                stdin, stdout, stderr = self.ssh.exec_command("mkdir -p {}".format(backupdir))
                stderr_txt = stderr.read().decode()
                if stderr_txt != '': raise IOError(stderr_txt)
                stdin, stdout, stderr = self.ssh.exec_command(
                    "/bin/cp -r {0}/*  {1}/".format(os.path.join(self._dstdir, i), backupdir))
                stderr_txt = stderr.read().decode()
                if stderr_txt != '': raise IOError(stderr_txt)
                self.backuplist.append(backupdir)
            except Exception as e:
                print('backup catch Exception', e)
                self.success_status = 'backup_fail'
                self.have_error = True
        else:
            if self.have_error:
                self.success_status = 'backup_fail'
            else:
                self.success_status = 'backup_success'

    def do_cover(self):
        """
        :param: self.ignore_new, 忽略新增
        :return:
        """
        self.ssh = self._remote_server.get_sshclient()
        self.sftp = self._remote_server.get_xftpclient()
        try:
            if self.ignore_new:
                """"创建新建文件夹"""
                for ndir in self.newdir:
                    abspath_path = os.path.join(self._dstdir, ndir)
                    stdin, stdout, stderr = self.ssh.exec_command('mkdir -p {}'.format(abspath_path))
                    stderr_txt2 = stderr.read().decode()
                    if stderr_txt2 != '':
                        raise IOError(stderr_txt2)
            for pub_file in self.unzipfilelist:
                # ignore == False, 不覆盖新增文件
                if not self.ignore_new and pub_file in self.newfile:
                    continue
                # print("Debug: cover file {}".format(pubfile))
                print('sftp put {} {}'.format(os.path.join(self._tmpdir, '_dist', pub_file),
                                              os.path.join(self._dstdir, pub_file)))
                self.sftp.put(os.path.join(self._tmpdir, '_dist', pub_file), os.path.join(self._dstdir, pub_file))

        except Exception as e:
            print("Unknown Exception as:", e)
            self.have_error = True
            self.rollback(onpub=True)
        finally:
            self._remote_server.sshclient_close()
            self._remote_server.xftpclient_close()
            self.success_status = 'pub_success'
            print("{} 发布完成！".format(self._fromfile))

    def rollback(self, onpub=False):
        """
        :param: onpub 正常发布状态， 出现失败回滚
        :return:
        """
        self.ssh = self._remote_server.get_sshclient()
        if onpub:
            self.success_status = 'pub_fail'
        else:
            self.success_status = "roll_back_success"
        for tdir in self.shouldbackdir:
            self.ssh.exec_command("mkdir -p /tmp/roll_back/")
            self.ssh.exec_command("mv {} /tmp/roll_back/".format(os.path.join(self._dstdir, tdir)))
            self.ssh.exec_command("mv {} {}".format(os.path.join(self._backup_ver, tdir),
                                                    os.path.join(self._dstdir, tdir)))
        self._remote_server.sshclient_close()
        self._remote_server.xftpclient_close()

    def cleantmp(self):
        shutil.rmtree(self._tmpdir)

    def pip_run(self):
        _lockkey = '{}_{}_0_lock'.format(self._pjtname, self._items, )
        record_id = '{0}_{1}_{2}_{3}'.format(self._pjtname, self._items, 0, self._pk)
        self.redis_cli.hmset(_lockkey, {'lock_task': record_id, 'starttime': self._operatingtime, })
        if not self.have_error:
            self.make_ready()
        if not self.have_error:
            self.do_backup()
        if not self.have_error:
            self.do_cover()
        self.redis_cli.delete(_lockkey)
        self.cleantmp()
        pub_status = 2  # 发布成功状态
        if RecordOfStatic.objects.filter(record_id=record_id).count() == 0:
            pub_filemd5sum = file_md5sum(self._fromfile)
            RecordOfStatic(pub_filemd5sum=pub_filemd5sum,
                           items=ProjectInfo.objects.get(items=self._items, platform=self._pjtname, type=self.pub_type),
                           record_id=record_id,
                           pub_status=pub_status).save()
        elif RecordOfStatic.objects.get(record_id=record_id).pub_status == 0:  # RecordOfStatic Exist， pub_status = 0
            record_line_info = RecordOfStatic.objects.get(record_id=record_id)
            record_line_info.pub_status = pub_status
            record_line_info.save()
        return {"Error": self.have_error, "status": self.success_status, "backup_ver": self._backup_ver,
                "backed_up_dir": self.shouldbackdir, "pub_ignore_new": self.ignore_new, "add_file": self.newfile,
                "add_dir": self.newdir, "update_file_list": self.unzipfilelist, }

    def test_run(self):
        _lockkey = '{}_{}_0_lock'.format(self._pjtname, self._items, )
        self.redis_cli.hmset(_lockkey, {'lock_task': 'test_run_task_id'})
        print('start_run')
        import time
        time.sleep(25)
        self.redis_cli.delete(_lockkey)
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
