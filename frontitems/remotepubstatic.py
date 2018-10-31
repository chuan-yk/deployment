#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
import os
import datetime
import tempfile
import shutil
from cmdb.models import ServerInfo
from .models import  ProjectInfo

class RemoteReplaceWorker(object):
    def __init__(self, serverinfo_instance, dstdir, fromfile, projectname, backupdir, shouldbackdir=set(), backup_ver='', ignore_new=True):
        """serverinfo_instance:服务器 ssh 实例
        dstdir:发布目的地址
        fromfile:发布源文件
        projectname:项目名
        backupdir:备份地址
        shouldbackdir: 备份文件夹，如 static/common , static/sobet, sobet
        backup_ver: 备份文件目录
        """
        self._remote_server = serverinfo_instance
        self._dstdir = dstdir
        self._fromfile = fromfile
        self._projectname = projectname
        self._backupdir = backupdir         #/date/release
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0 :
            self._backup_ver = os.path.join(self._backupdir, '{}_Ver_{}'.format(self._projectname, self._operatingtime))
        else:
            self._backup_ver = backup_ver
        self.ignore_new = ignore_new
        self.unzipfilelist = []     # 文件夹列表
        self.unzipdirlist = []      # 文件列表
        self.shouldbackdir = shouldbackdir     # 发布文件子目录，对改目录进行备份
        self.backuplist = []        # 备份文件列表
        self.newdir = []            # 新增文件夹
        self.newfile = []           # 新文件
        self.success_status = ''
        self.have_error = False
        if tempfile.tempdir == None:
            os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
            tempfile.tempdir = os.path.join(os.getcwd(), 'tmp')
        self._tmpdir = tempfile.mkdtemp(prefix=projectname+'_', suffix='_django')
        self.ssh = None
        self.sftp = None

    def make_ready(self):
        try:
            shutil.unpack_archive(self._fromfile, extract_dir=self._tmpdir, format='zip')
            if not os.path.isdir(os.path.join(self._tmpdir, '_dist')):
                raise IOError('could not find _dist dir under tempdir {0}'.format(self._tmpdir))
            for root, dirs, files in os.walk(os.path.join(self._tmpdir, '_dist/'), topdown=False, followlinks=False):
                for dir in dirs:
                    self.unzipdirlist.append(os.path.join(root.split('_dist/')[1], dir))     # 类似： '/tmp/xxx/_dist/static/sobet'.split('_dist'), css
                for file in files:
                    self.unzipfilelist.append(os.path.join(root.split('_dist/')[1], file))   #
            # 需备份文件夹
            for seconddir in self.unzipdirlist:
                if seconddir.split('/').__len__() < 3 and seconddir != 'static':
                    self.shouldbackdir.add(seconddir)
            for file in self.unzipfilelist:
                if not self._remote_server.if_exist_file(os.path.join(self._dstdir, file)):
                    self.newfile.append(file)
            for dir in self.unzipdirlist:
                if not self._remote_server.if_exist_dir(os.path.join(self._dstdir, dir)):
                    self.newdir.append(dir)
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
                self.ssh.exec_command("mkdir -p {}".format(backupdir))
                stdin, stdout, stderr = self.ssh.exec_command("/bin/cp -r {0}/*  {1}".format(os.path.join(self._dstdir, i) , backupdir ))
                stderr_txt = stderr.read().decode()
                if stderr_txt != '':
                    raise IOError(stderr_txt)
                self.backuplist.append(backupdir)
            except Exception as e:
                print('backup catch Exception', e)
                self.success_status = 'backup_fail'
                self.have_error = True
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
            for pubfile in self.unzipfilelist:
                # ignore == False, 不覆盖新增文件
                if not self.ignore_new and pubfile in self.newfile:
                    continue
                print("Debug: cover file {}".format(pubfile))
                print('sftp put {} {}'.format(os.path.join(self._tmpdir, '_dist', pubfile),
                                              os.path.join(self._dstdir, pubfile)))
                stdin, stdout, stderr = self.sftp.put(os.path.join(self._tmpdir, '_dist', pubfile), os.path.join(self._dstdir, pubfile))
                stderr_txt3 = stderr.read().decode()
                if stderr_txt3 != '':
                    raise IOError(stderr_txt3)
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
        return {"task_status": self.have_error,"status": self.success_status, "backup_ver": self._backup_ver, "backed_up_dir": self.shouldbackdir,
                "pub_ignore_new": self.ignore_new, "add_file": self.newfile, "add_dir": self.newdir,
                "update_file_list": self.unzipfilelist, }


if __name__ == "__main__":
    import paramiko
    import os
    import sys
    import django
    import django_manage_shell

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "D:\\deployment\\deployment\\deployment.settings.py")
    sys.path.extend(['D:\\deployment', 'D:\\Program Files\\PyCharm 2018.1.4\\helpers\\pycharm',
                     'D:\\Program Files\\PyCharm 2018.1.4\\helpers\\pydev'])
    django.setup()
    django_manage_shell.run()
    pkey = paramiko.RSAKey.from_private_key_file("C:\\Users\\ice\\.ssh\\id_rsa")
    serverinfo_150 = ServerInfo.objects.get(pk=1)
    print(serverinfo_150)
    p = ProjectInfo.objects.get(package_name="sobet.zip")
    dst = p.static_dir
    fromfile1 = "tmp/sobet.zip"
    projectname1 = p.items
    backupdir = p.file_save_base_dir
    rmt_tasker = RemoteReplaceWorker(serverinfo_150, dst, fromfile1, projectname1, backupdir)
    rmt_tasker.pip_run()