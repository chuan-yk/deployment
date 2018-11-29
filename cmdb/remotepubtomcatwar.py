#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-

import os
import datetime
import shutil
from django_redis import get_redis_connection

from cmdb.models import ProjectInfo
from tomcatwar.models import RecordOfwar
from fileupload.models import Fileupload


class RemoteWarReplaceWorker(object):
    def __init__(self, serverinfo_instance, fileupload_instace, projectinfo_instance, records_instance,
                 backup_ver='', ):
        """serverinfo_instance:服务器 ssh 实例
        fileupload_instace: 文件上传行内容
        backup_ver: 备份所在文件夹
        """
        # Debug #fileupload_instace = Fileupload.objects.get(pk=11)
        # Debug #projectinfo_instance = fileupload_instace.project
        # Debug #records_instance = RecordOfwar.objects.get(pk=2)
        self.remote_server = serverinfo_instance
        self.fileupload_instace = fileupload_instace
        self.projectinfo_instance = projectinfo_instance
        self.records_instance = records_instance
        self._dstdir = projectinfo_instance.dst_file_path  # 发布目标地址
        self._fromfile = fileupload_instace.file.path  # 上传文件
        self._pjtname = projectinfo_instance.platform  # 平台名
        self._items = projectinfo_instance.items  # 项目名
        self._backupdir = projectinfo_instance.backup_file_dir  # 约定平台备份路径，/date/mc
        self.configlist = self.projectinfo_instance.output_configs()
        self._pk = fileupload_instace.pk  # 文件上传编号
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0:
            self._backup_ver = os.path.join(self._backupdir, 'war_{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver  # 约定平台下项目备份路径 /data/mc/[sobet_Ver_日期]
        self.redis_cli = get_redis_connection("default")  # redis 客户端
        self.success_status = ''
        self.have_error = False
        self.error_reason = ''
        self._tmpdir = False  # 远程服务器临时文件夹
        self._remote_filename = ''  # 远程服务器war 包文件
        self._remote_unzipdir = ''  # 远程服务器war 包解压路径
        self.pub_type = fileupload_instace.type  # 发布类型 1：静态文件
        self.record_id = self.records_instance.record_id  # '{0}:{1}:{2}:{3}'.format(self._pjtname, self._items, self.pub_type, self._pk)
        self._lockkey = '{}:{}:{}:lock'.format(self._pjtname, self._items, self.pub_type)
        self.ssh = None
        self.sftp = None
        # print("debug class init:", self.shouldbackdir)

    def checkfiledetail(self):
        """检查文件详情，存redis """
        return None
        if self.redis_cli.exists(self.record_id):
            # print("Debug: redis 键值 {} 已存在".format(self.record_id))
            tmp_getall = self.redis_cli.hgetall(self.record_id, )
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
                    current_file_md5 = 'x'
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
            RecordOfStatic.objects.filter(pk=self.records_instance.pk).update(pub_status=pub_status)  # 发布状态更改为3
        self.cleantmp()
        return self.md5dict

    def make_ready(self):
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()
        try:
            stdin, stdout, stderr = self.ssh.exec_command(
                "mktemp -t -d upload_{}_{}_.XXXX".format(self._pjtname, self._items))
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                raise IOError(err_str1)
            else:
                self._tmpdir = stdout.read().decode()
                self._remote_filename = os.path.join(self._tmpdir, self.fileupload_instace.slug)
                self._remote_unzipdir = os.path.join(self._tmpdir, self._items)
            self.sftp.put(self._fromfile, self._remote_filename)
            stdin, stdout, stderr = self.ssh.exec_command("""if [ `which unzip 2>/dev/null`'x' == 'x' ]; then 
                yum install -y unzip ; fi ;
                mkdir -p {0};
                unzip -qo {1} -d {0}""".format(self._remote_unzipdir, self._remote_filename, )
                                                          )
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                raise IOError(err_str1)
            for configfile in self.configlist:
                self.ssh.exec_command(
                    """/bin/cp {} {}""".format(os.path.join(self._dstdir, configfile),
                                               os.path.join(self._remote_unzipdir, configfile)))
            #  配置文件修改功能在此补充
        except Exception as e1:
            self.have_error = True
            self.error_reason = str(e1)
            self.success_status = "unzip_failed"
            print('Error e1:', e1)
            print("Error: ", "远程解压War文件过程异常")
        if not self.have_error:
            self.success_status = 'unziped_success'

    def do_backup(self):
        self.ssh = self.remote_server.get_sshclient()
        try:
            stdin, stdout, stderr = self.ssh.exec_command("""mkdir -p {0} {0}_mv_as_remove; 
            chown -R {1}:{1} {0} {0}_mv_as_remove""".format(self._backup_ver, self.projectinfo_instance.runuser))
            str_err2 = stderr.read().decode()
            if str_err2 != "":
                raise IOError(str_err2)
            stdin, stdout, stderr = self.ssh.exec_command(
                """cp -r {0} {1}""".format(os.path.join(self._dstdir, self._items), self._backup_ver))
            str_err2 = stderr.read().decode()
            if str_err2 != "":
                raise IOError(str_err2)
        except Exception as e3:
            self.have_error = True
            self.error_reason = str(e3)
            self.success_status = "backup_failed"
            print('Error e1:', e3)
        if not self.have_error:
            print("{0} Info: {1} Backup old file success~\ncp -r {2} {3}".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server,
                os.path.join(self._dstdir, self._items), self._backup_ver))
            self.success_status = "backup_success"

    def stop_tomcat(self):
        """停止tomcat进程"""
        try:
            # 检查进程
            stdin, stdout, stderr = self.ssh.exec_command("""
                            ps -ef|grep java |grep -v 'grep'|grep {0}/conf 
                        """.format(os.path.dirname(self._dstdir)))
            err_str1 = stderr.read().decode()
            stdout_str = stdout.read().decode()
            print("{0}   Info: {1}检测tomcat进程详情为\n{2}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                             self.remote_server, stdout_str))
            if err_str1 != '':
                raise IOError(err_str1)
            # 结束tomcat进程
            print("{0}   Info: {1} Start kill {2} java进程, continue".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server, self._dstdir))
            stdin, stdout, stderr = self.ssh.exec_command(
                """ps -ef|grep java |grep {0}/conf """.format(os.path.dirname(self._dstdir)) +
                "|awk '{print $2}' |xargs kill -9 ")
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                raise IOError(err_str1)
            print("{0}   Info: {1} kill {2} java进程成功, continue".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server, self._dstdir))
        except Exception as e:
            except_str = "{0}   Info: {1} 停止tomcat {2}进程失败\n{3}".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.remote_server, self._dstdir, str(e))
            print(except_str)
            self.have_error = True
            self.error_reason = except_str
            self.success_status = "stop tomcat failure"
        if not self.have_error:
            self.success_status = "stop tomcat successful"

    def start_tomcat(self):
        """Start tomcat , reuse"""
        self.ssh = self.remote_server.get_sshclient()
        try:
            # 检查目录赋权
            stdin, stdout, stderr = self.ssh.exec_command(
                "chown -R {0}:{0} {1}".format(self.projectinfo_instance.runuser, self._dstdir))
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                raise IOError(err_str1)
            print("{0} Debug: {1} 启动tomcat ，操作详情 su {2} -c '{3}/bin/startup.sh' ".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server,
                self.projectinfo_instance.runuser, os.path.dirname(self._dstdir)))
            stdin, stdout, stderr = self.ssh.exec_command(
                "su {0} -c '{1}/bin/startup.sh'".format(self.projectinfo_instance.runuser,
                                                        os.path.dirname(self._dstdir)))
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                raise IOError(err_str1)
        except Exception as e:
            except_str = "{0}   Info: {1} 启动tomcat {2}进程失败\n{3}".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.remote_server, self._dstdir, str(e))
            print(except_str)
            self.have_error = True
            self.error_reason = except_str
            self.success_status = 'Start tomcat failure'
        if not self.have_error:
            self.success_status = 'pub_success'
            print("{0} Info: {1} 启动tomcat完成，操作详情 su {2} -c '{3}/bin/startup.sh' ".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server,
                self.projectinfo_instance.runuser, os.path.dirname(self._dstdir)))

    def do_cover(self):
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()
        try:
            # 维护状态检测，在此补充
            # 删除webapps下旧项目
            stdin, stdout, stderr = self.ssh.exec_command(
                "mv {0} {1}_mv_as_remove".format(os.path.join(self._dstdir, self._items), self._backup_ver))
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                print("{0}   Error: {1}移除tomcat异常，详情 mv {2} {3}_mv_as_remove".format(
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server,
                    os.path.join(self._dstdir, self._items), self._backup_ver))
                self.start_tomcat()
                raise IOError(err_str1)
            print("{0} Info: {1}删(移)除{2}， 详情 mv {2} {3}_mv_as_remove".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server,
                os.path.join(self._dstdir, self._items), self._backup_ver))
            # 更新webapps ，放入更新文件
            stdin, stdout, stderr = self.ssh.exec_command("""mv  {0} {1}""".format(self._remote_unzipdir, self._dstdir))
            err_str1 = stderr.read().decode()
            if err_str1 != '':
                print("{0} Error: {1} 更新文件失败，自动回滚，错误详情 mv {2} {3}".format(
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server, self._remote_unzipdir,
                    self._dstdir))
                self.autoturnback()
                self.start_tomcat()
                raise IOError(err_str1 + '更新文件移入webapps 出错，发布自动回滚并重启')
            print("{0} Error: {1} 更新文件成功，操作详情 mv {2} {3}".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server, self._remote_unzipdir,
                self._dstdir))
        except FileNotFoundError as e:  # 捕获xftp put 过程目的文件夹不存在的异常
            print('Sftp put file error', e)
            self.have_error = True
            self.error_reason = str(e)
            self.success_status = 'do cover failed'
        except IOError as e1:
            self.have_error = True
            self.error_reason = str(e1)
            self.success_status = 'do cover failed'
        if not self.have_error:
            self.success_status = "restart successful"

    def autoturnback(self):
        """还原更新过程"""
        stdin, stdout, stderr = self.ssh.exec_command(
            """/bin/mv -b {0}/* {1}_mv_as_remove/ ;mv  {2} {0}""".format(self._dstdir, self._backup_ver,
                                                                         os.path.join(self._backup_ver, self._items), ))
        err_str1 = stderr.read().decode()
        print("{0} Info: {1} 自动还原过程，操作详情 /bin/mv -b {2}/* {3}_mv_as_remove/ ;\n mv  {4} {2}".format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.remote_server, self._dstdir, self._backup_ver,
            os.path.join(self._backup_ver, self._items)))
        if err_str1 != '':
            print("{0} Info: {1} 发布异常，自动还原失败".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                     self.remote_server))

    def checkbackdir(self):
        """还原过程检查备份文件是否存在"""
        self.ssh = self.remote_server.get_sshclient()
        if self.remote_server.if_exist_dir(os.path.join(self._backup_ver, self._items)):
            return True
        else:
            return False

    def rollback(self):
        """回滚"""
        self.ssh = self.remote_server.get_sshclient()
        try:
            print("{0} Info: {1} 创建目录 {2}_rollback".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                           self.remote_server, self._backup_ver))
            stdin, stdout, stderr = self.ssh.exec_command("""mkdir -p  {0}_rollback; 
                    chown -R {1}:{1}  {0}_rollback""".format(self._backup_ver, self.projectinfo_instance.runuser))
            str_err2 = stderr.read().decode()
            if str_err2 != "":
                raise IOError(str_err2)
            print("{0} Info: {1} 还原备份目录\n详情：/bin/cp -r {2} {3}".format(self.remote_server, self._dstdir,
                                                                       os.path.join(self._backup_ver, self._items),
                                                                       self._dstdir))
            stdin, stdout, stderr = self.ssh.exec_command(
                "/bin/cp -r {0} {1}".format(os.path.join(self._backup_ver, self._items), self._dstdir))
            str_err2 = stderr.read().decode()
            if str_err2 != "":
                raise IOError(str_err2)
        except Exception as e:
            print("{0} {1}回滚过程异常:{2}".format(self.remote_server, self._dstdir, str(e)))
        if not self.have_error:
            self.success_status = "roll file back success"

    def cleantmp(self):
        shutil.rmtree(self._tmpdir)

    def pip_run(self):

        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        self.redis_cli.hmset(self.record_id, {'error_detail': self.error_reason})  # 初始化，error_detail
        self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=1, )  # 修改发布状态
        Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=1, )  # 修改发布状态
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'upload file to Remote server'})  # 发布过程更新状态
        if not self.have_error:
            self.do_backup()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})  # 发布过程更新状态
        if not self.have_error:
            self.stop_tomcat()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.do_cover()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.start_tomcat()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        self.redis_cli.delete(self._lockkey)
        self.cleantmp()
        RecordOfwar.objects.filter(pk=self.records_instance.pk).update(
            backupsavedir=self._backup_ver, )  # 更新records 记录
        self.records_instance.refresh_from_db()  # 重新读取数据库值
        if self.have_error:
            RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=-1, )  # 修改发布状态
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=-1, )  # 修改发布状态
            self.redis_cli.hmset(self.record_id, {'error_detail': self.success_status + ': ' + self.error_reason})
            self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        else:
            RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=2, )  # 修改发布状态
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=2, )  # 修改发布状态

    def rollback_run(self):
        self.ssh = self.remote_server.get_sshclient()
        self.success_status = "roll_back_Start"
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        self.redis_cli.hmset(self.record_id, {'error_detail': self.error_reason})  # 初始化，error_detail
        print("{0} Info: {1}  {2}开始回滚操作".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                self.remote_server, self._dstdir))
        RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=4)
        if not self.have_error:
            self.stop_tomcat()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.rollback()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        if not self.have_error:
            self.start_tomcat()
            self.redis_cli.hmset(self._lockkey, {'pub_current_status': self.success_status})
        self.redis_cli.delete(self._lockkey)
        if self.have_error:
            RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=-2)
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=-2)
        else:
            RecordOfwar.objects.filter(pk=self.records_instance.pk).update(pub_status=5)
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=0)

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
