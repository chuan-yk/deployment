#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
import os
import datetime
import tempfile
import shutil
import paramiko
from django_redis import get_redis_connection


class RemoteReplaceWorker(object):
    def __init__(self, serverinfo_instance, dstdir, fromfile, platfrom, items, backupdir, shouldbackdir=set(),
                 backup_ver='', ignore_new=True, tmpdir='/tmp'):
        """serverinfo_instance:服务器 ssh 实例
        dstdir:发布目的地址
        fromfile:发布源文件
        platfrom:平台名称
        items:项目名
        backupdir:备份约定目录
        shouldbackdir: 备份文件夹，如 static/common , static/sobet, sobet
        backup_ver: 备份所在文件夹
        """
        self._remote_server = serverinfo_instance
        self._dstdir = dstdir
        self._fromfile = fromfile
        self._pjtname = platfrom
        self._items = items
        self._backupdir = backupdir         # /date/release
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0 :
            self._backup_ver = os.path.join(self._backupdir, '{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver
        self.ignore_new = ignore_new
        self.redis_cli = get_redis_connection("default")
        self.unzipfilelist = []     # 文件夹列表
        self.unzipdirlist = []      # 文件列表
        self.shouldbackdir = shouldbackdir     # 发布文件子目录，对改目录进行备份
        self.backuplist = []        # 备份文件列表
        self.newdir = []            # 新增文件夹
        self.newfile = []           # 新文件
        self.success_status = ''
        self.have_error = False
        if tmpdir != '':
            tempfile.tempdir = tmpdir
        else:
            os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
            tempfile.tempdir = os.path.join(os.getcwd(), 'tmp')
        self._tmpdir = tempfile.mkdtemp(prefix=items+'_', suffix='_django')
        self.ssh = None
        self.sftp = None

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
                    self.unzipfilelist.append(os.path.join(root.split('_dist/')[1], file))   #
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
                backupdir = os.path.join(self._backup_ver, i)   #备份完整路径 /xxx/xx/项目/project_201YddHHMMSS/
                stdin, stdout, stderr = self.ssh.exec_command("mkdir -p {}".format(backupdir))
                stderr_txt = stderr.read().decode()
                if stderr_txt != '': raise IOError(stderr_txt)
                stdin, stdout, stderr = self.ssh.exec_command("/bin/cp -r {0}/*  {1}/".format(os.path.join(self._dstdir, i) , backupdir ))
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



    def pip_run(self):
        if not self.have_error:
            self.make_ready()
        if not self.have_error:
            self.do_backup()
        if not self.have_error:
            self.do_cover()
        return {"task_status": self.have_error,"status": self.success_status, "backup_ver": self._backup_ver,
                "backed_up_dir": self.shouldbackdir, "pub_ignore_new": self.ignore_new, "add_file": self.newfile,
                "add_dir": self.newdir, "update_file_list": self.unzipfilelist, }


