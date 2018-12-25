#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
import os
import datetime
import tempfile
import shutil
import json
import logging
from django_redis import get_redis_connection

from cmdb.models import ProjectInfo
from cmdb.mytools import file_md5sum
from tomcatjar.models import RecordOfjavajar
from fileupload.models import Fileupload

# Django logger
logger = logging.getLogger('django.scripts')


class RemoteZipReplaceWorker(object):
    def __init__(self, serverinfo_instance, fileupload_instace, projectinfo_instance, records_instance,
                 backup_ver='', ):
        """serverinfo_instance:服务器 ssh 实例
        fileupload_instace: 文件上传行内容
        backup_ver: 备份所在文件夹
        """
        # Debug # fileupload_instace = Fileupload.objects.get(pk=12)
        # Debug # projectinfo_instance = fileupload_instace.project
        # Debug # records_instance = RecordOfjavajar.objects.get(pk=1)
        self.remote_server = serverinfo_instance
        self.fileupload_instace = fileupload_instace
        self.projectinfo_instance = projectinfo_instance
        self.records_instance = records_instance
        self._dstdir = projectinfo_instance.dst_file_path  # 发布目标地址
        self._fromfile = fileupload_instace.file.path  # 上传文件
        self._pjtname = projectinfo_instance.platform  # 平台名
        self._items = projectinfo_instance.items  # 项目名
        self._backupdir = projectinfo_instance.backup_file_dir  # 约定平台备份路径，/date/java_jar
        self.configlist = self.projectinfo_instance.output_configs()
        self._pk = fileupload_instace.pk  # 文件上传编号
        self._operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(backup_ver) == 0:
            self._backup_ver = os.path.join(self._backupdir, 'jar_{}_Ver_{}'.format(self._items, self._operatingtime))
        else:
            self._backup_ver = backup_ver  # 约定平台下项目备份路径 /data/mc/[jar_sobet_Ver_日期]
        self.redis_cli = get_redis_connection("default")  # redis 客户端
        self.process_status = []  # 进程执行状态
        self.have_error = False
        self.error_reason = ''
        self._tmpdir = ''  # 远程服务器临时文件夹
        self._localtmpdir = ''  # 本地临时解压目录
        self._remote_filename = ''  # 远程服务器war 包文件
        self._remote_unzipdir = ''  # 远程服务器war 包解压路径
        self.pub_type = fileupload_instace.type  # 发布类型 3 jar 增量文件
        self.record_id = self.records_instance.record_id  # '{0}:{1}:{2}:{3}'.format(self._pjtname, self._items, self.pub_type, self._pk)
        self.jarname = os.path.splitext(self.fileupload_instace.slug)[0]  # Jar 文件名
        self.tomcathome = self.projectinfo_instance.dst_file_path.split('webapps')[0]
        self._lockkey = '{}:{}:{}:lock:{}'.format(self._pjtname, self._items, self.pub_type, self.jarname)
        self.readmelist = []  # readme 发布文件列表
        self.md5dict = {}  # 解压文件MD5记录
        self.new_filemd5 = ''  # 更新后的jar 文件MD5
        self.ssh = self.remote_server.get_sshclient()
        self.sftp = self.remote_server.get_xftpclient()

    # def mylogway(self, logstr, level="Error"):
    #     """自定义日志打印"""
    #     # if level.capitalize() in ["Error", "Info", ]:  # 调整日志级别
    #     if level.capitalize() in ["Error", "Info", "Debug", ]:  # 调整日志级别
    #         print("{0}   [{1}]: {2} {3} {4}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level,
    #                                                 self.remote_server, self.record_id, logstr))

    def mylogway(self, logstr, level="Error"):
        if level.capitalize() == 'Error':
            logger.error("{} {} {}".format(self.remote_server, self.record_id, logstr))
        if level.capitalize() == 'Info':
            logger.info("{} {} {}".format(self.remote_server, self.record_id, logstr))
        if level.capitalize() == 'Debug':
            logger.debug("{} {} {}".format(self.remote_server, self.record_id, logstr))

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
            self.mylogway("执行远程命令失败: {} , 交互参数 stdin = {}".format(cmd, stdinstr), "Error")
            raise IOError(stderr_str)
        return stdout_str

    def rdreadme(self, file):
        """readme 文件处理"""
        import re
        readmelist = []
        with open(file, 'r') as f:
            lines = f.readlines()
            for i in lines:
                i = i.strip()  # 去掉前后空格、换行符
                i = i.replace('\\', '/')
                i = i.strip('/')
                # i = i.replace('$', '\$')
                if not re.match(r'^#', i) and i != '':
                    readmelist.append(i)
        return readmelist

    def transmitprocessstatus(self):
        pass

    def checkfiledetail(self):
        """检查文件详情，存redis """
        # 本地解压，读取readme
        try:
            if self.redis_cli.exists("self.record_id"):
                md5dict = self.redis_cli.hget(self.record_id, 'md5list').decode()
                self.md5dict = json.loads(md5dict)
                self.readmelist = self.records_instance.output_changefiles()
                self.mylogway("读取redis {} hget {}, 获取跟新文件 MD5 列表".format(self.record_id, 'md5list'), level='Debug')
                self.jarname = self.redis_cli.hget(self.record_id, 'jarname').decode()
                self.mylogway("读取redis {} hget {}, 获取 Jar 文件名为 {}".format(self.record_id, 'jarname', self.jarname),
                              level='Debug')
                return self.md5dict
        except Exception as e:
            pass
        try:
            self._localtmpdir = tempfile.mkdtemp(prefix=self._items + '_', suffix='jar_zip')
            shutil.unpack_archive(self._fromfile, extract_dir=self._localtmpdir, format='zip')
            self.readmelist = self.rdreadme(os.path.join(self._localtmpdir, 'readme.txt'))  # 读取readme 内容
            self.mylogway("读取readme.txt, readme 内容为：{}".format(str(self.readmelist)), level='info')
            lclunziplist = os.listdir(self._localtmpdir)
            lclunziplist.remove('readme.txt')
            if len(lclunziplist) != len(self.readmelist):
                self.mylogway("""解压文件包含 {} 个文件，不匹配readme {}行记录，请联系更新包上传人员\n 
                    解压文件为: {} , readme 内容为 {}""".format(len(lclunziplist), len(self.readmelist), lclunziplist,
                                                        self.readmelist), level='Error')
                raise IOError("upload file less than readme.txt ")
            for i in self.readmelist:
                if not os.path.isfile(os.path.join(self._localtmpdir, os.path.basename(i))):
                    self.mylogway(
                        "readme.txt 包含文件{}, 该文件{}未上传".format(i, os.path.join(self._localtmpdir, os.path.basename(i))),
                        level='Error')
                    raise IOError("upload file No match (less than) readme.txt ")
                self.md5dict[i] = file_md5sum(os.path.join(self._localtmpdir, os.path.basename(i)))
                self.mylogway("记录jar: {} 增量更新文件 MD5 = {} -- {} ".format(
                    self.jarname, self.md5dict[i], i), level='Debug')

            else:
                self.mylogway("录入redis md5dict, hmset {} ， {}".format(self.record_id, json.dumps(self.md5dict)),
                              level='Debug')

                self.redis_cli.hmset(self.record_id, {'md5list': json.dumps(self.md5dict), 'jarname': self.jarname})
                self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        except Exception as e:
            self.mylogway("解压文件过程发现异常， 错误详情{}".format(e))
            self.have_error = True
            self.error_reason = "解压文件过程发现异常， 错误详情{}".format(e)

    def make_ready(self):
        """上传、解压、检查文件内容"""
        try:
            # 调用checkfiledetail本地解压，读取readme, 检查更新文件是否与更新文件冲突
            self.checkfiledetail()
            if self.have_error:
                return None
            # 上传解压
            self._tmpdir = self.myexecute("mktemp -t -d jarupload_{}_{}_.XXXX".format(self._pjtname, self._items))
            self.mylogway("创建远程服务器临时文件夹 {}".format(self._tmpdir), level="Debug")
            self._remote_filename = os.path.join(self._tmpdir, self.fileupload_instace.slug)
            self._remote_unzipdir = os.path.join(self._tmpdir, self._items)  # 服务器上的 解压jar.zip 目录
            self.myexecute("mkdir -p {}".format(self._remote_unzipdir))
            self.mylogway("创建远程服务器解压存放临时文件夹 {}".format(self._remote_unzipdir), level="Debug")
            self.sftp.put(self._fromfile, self._remote_filename)
            self.mylogway("上传文件 {} 至 {}".format(self._fromfile, self._tmpdir), level="Debug")
            self.myexecute("""if [ `which unzip 2>/dev/null`'x' == 'x' ]; then 
                                        yum install -y unzip ; fi ;
                                        mkdir -p {0};
                                        unzip -qo {1} -d {0}""".format(self._remote_unzipdir, self._remote_filename))
            self.mylogway("解压文件成功， 临时目录{}".format(self._remote_filename), level="Debug")
            # 适配现阶段jar.zip 打包方式，自动转接目录
            for ff in self.readmelist:
                self.myexecute("mkdir -p '{}' ".format(os.path.join(self._remote_unzipdir, os.path.dirname(ff))))
                self.myexecute("mv '{}' '{}' ".format(os.path.join(self._remote_unzipdir, os.path.basename(ff)),
                                                      os.path.join(self._remote_unzipdir, os.path.dirname(ff))))
            else:
                self.myexecute("rm -f {}/readme.txt".format(self._remote_unzipdir))
        except Exception as e1:
            self.have_error = True
            self.error_reason = str(e1)
            self.process_status.append("unzip_failed")
            self.mylogway("zip 文件不符合规范 或远程解压异常, 详情 {}".format(e1), level="Error")
        if not self.have_error:
            self.process_status.append('unziped_success')

    def do_backup(self):
        self.ssh = self.remote_server.get_sshclient()
        # 备份单个jar 文件
        try:
            self.myexecute("mkdir -p {0} {0}_mv_as_remove; chown -R {1}:{1} {0} {0}_mv_as_remove".format(
                self._backup_ver, self.projectinfo_instance.runuser))
            self.myexecute("cp -r '{0}'  '{1}'".format(os.path.join(self._dstdir, self.jarname), self._backup_ver))
            self.mylogway("备份文件完成: {}".format(self._backup_ver), level="Info")
        except Exception as e3:
            self.have_error = True
            self.error_reason = str(e3)
            self.process_status.append("backup_failed")
            self.mylogway("备份文件失败: {}".format(e3), level="Error")
            return None

        if not self.have_error:
            self.process_status.append("backup_success")

    def stop_tomcat(self):
        """停止tomcat进程"""
        try:
            # 检查进程
            tpro = self.myexecute(
                "ps -ef|grep java |grep -v grep|grep {0} ".format(os.path.join(self.tomcathome, 'conf')))
            self.mylogway("进程返回结果长度为：{}, 检测tomcat进程为{}".format(len(tpro), ': \n' + str(tpro)), level="Info")
            if not len(tpro):
                self.mylogway("当前{} JAVA 进程未启动，跳出 stop 函数".format(self.fileupload_instace.slug), level="Info")
                return None  # 进程未启动，跳出stop
            # 结束tomcat进程
            self.myexecute("ps -ef|grep java |grep -v grep|grep {0}".format(
                os.path.join(self.tomcathome, 'conf')) + "|awk '{print $2}' |xargs kill -9 ")
            self.mylogway("kill {} java进程成功, continue".format(self.projectinfo_instance.items), level="Info")
        except Exception as e:
            self.have_error = True
            self.mylogway("结束 tomcat 进程异常, 详情{}".format(e), level="Error")
            self.process_status.append("stop tomcat failure")
        if not self.have_error:
            self.process_status.append("stop tomcat successful")

    def start_tomcat(self):
        """Start tomcat , reuse"""
        try:
            # 检查目录赋权
            self.myexecute("chown -R {0}:{0} {1}".format(self.projectinfo_instance.runuser, self._dstdir))
            self.myexecute("su {0} -c '{1}'".format(self.projectinfo_instance.runuser,
                                                    os.path.join(self.tomcathome, 'bin/startup.sh')))
            pro = self.myexecute(
                "ps -ef|grep java |grep -v grep|grep {0}".format(os.path.join(self.tomcathome, 'conf')))
            if len(pro):
                self.mylogway("启动tomcat 成功，新进程详情: \n{}".format(pro), level="Info")
        except Exception as e:
            self.mylogway("启动tomcat 进程失败,详情{}".format(e), 'Error')
            self.have_error = True
            self.error_reason = str(e)
            self.process_status.append('Start tomcat failure')
        if not self.have_error:
            self.process_status.append('Start tomcat success')

    def do_cover(self):
        try:
            # 维护状态检测功能，在此补充
            self.myexecute("cd {}; jar -uf {} ./* ".format(self._remote_unzipdir,
                                                           os.path.join(self._dstdir, self.jarname), ))
            self.new_filemd5 = self.myexecute("md5sum {}".format(os.path.join(self._dstdir, self.jarname)))
            self.mylogway("更新jar 文件成功")
        except Exception as e:
            self.mylogway("更新文件过程异常，详情{}\n开始自动还原...".format(e), level="Error")
            self.have_error = True
            self.error_reason = str(e)
            self.autoturnback()
            self.start_tomcat()

        if not self.have_error:
            self.process_status.append("renew successful")

    def autoturnback(self):
        """发布过程异常，还原更新过程，脏数据 mv 到 {self._backup_ver}_mv_as_remove"""
        try:
            self.myexecute(
                "/bin/mv -b '{0}' {1}_mv_as_remove/ ;mv {2} {0}".format(os.path.join(self._dstdir, self.jarname),
                                                                        self._backup_ver,
                                                                        os.path.join(self._backup_ver, self.jarname)))
            self.mylogway("自动还原完成，已恢复初始状态 ！", level="Error")
        except Exception as e:
            self.mylogway("自动还原也失败了，运维看日志排查问题吧 ！", level="Error")

    def checkbackdir(self):
        """web 请求还原过程检查备份文件是否存在"""
        if self.remote_server.if_exist_file(os.path.join(self._backup_ver, self.jarname)):
            return True
        else:
            return False

    def rollback(self):
        """用户手动回滚"""
        try:
            self.mylogway("创建目录 {}_rollback".format(self._backup_ver), level='Info')
            self.myexecute("mkdir -p  {0}_rollback; chown -R {1}:{1}  {0}_rollback".format(self._backup_ver,
                                                                                           self.projectinfo_instance.runuser))
            self.myexecute(
                "/bin/mv -b {} {}_rollback/".format(os.path.join(self._dstdir, self.jarname), self._backup_ver))
            self.myexecute("/bin/cp -r {0} {1}".format(os.path.join(self._backup_ver, self.jarname),
                                                       os.path.join(self._dstdir, self.jarname)))
        except Exception as e:
            self.mylogway("回滚过程出现异常，原因{}".format(e), level="Info")
        if not self.have_error:
            self.mylogway("回滚功能，回滚文件完成，下一步启动JAVA进程", level="Info")
            self.process_status.append("roll file back success")

    def cleantmp(self):
        # shutil.rmtree(self._tmpdir)
        try:
            if os.path.isdir(self._localtmpdir):
                shutil.rmtree(self._localtmpdir)
        except Exception as e1:
            self.mylogway("删除文件临时目录 {} 失败，原因{}".format(self._localtmpdir, str(e1)), level="Error")
        try:
            if len(self._tmpdir) < 4:
                raise IOError("远程临时目录变量 {} 为空，无法删除".format(self._tmpdir))
            self.myexecute("rm -rf {}".format(self._tmpdir))
            self.mylogway("删除远程文件临时目录 {} 完成 ".format(self._tmpdir), level="Info")
        except Exception as e:
            self.mylogway("删除远程文件临时目录 {} 失败，原因{}".format(self._tmpdir, str(e)), level="Error")

    def pip_run(self):
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        self.redis_cli.hmset(self.record_id, {'error_detail': self.error_reason})  # 初始化，error_detail
        self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
        RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=1, )  # 修改发布状态
        Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=1, )  # 修改发布状态
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'upload file to Remote server'})  # 发布过程更新状态
        # 依次执行函数
        for myfunc in [self.make_ready, self.do_backup, self.stop_tomcat, self.do_cover, self.start_tomcat]:
            if not self.have_error:
                myfunc()
                self.redis_cli.hmset(self._lockkey, {'pub_current_status': str(self.process_status)})  # 发布过程更新状态
        self.redis_cli.hmset(self._lockkey, {'pub_current_status': 'pub successful !'})
        self.redis_cli.delete(self._lockkey)
        self.cleantmp()
        # 更新records 记录
        self.records_instance.jarfilename = self.jarname
        self.records_instance.input_changefiles(self.readmelist)
        self.records_instance.backupsavedir = self._backup_ver
        self.records_instance.new_filemd5sum = self.new_filemd5
        self.records_instance.save()
        self.redis_cli.delete(self._lockkey)
        if self.have_error:
            RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=-1, )  # 修改发布状态
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=-1, )  # 修改发布状态
            self.redis_cli.hmset(self.record_id, {'error_detail': str(self.process_status) + ': ' + self.error_reason})
            self.redis_cli.expire(self.record_id, 60 * 60 * 24 * 14)
            self.mylogway("发布流程结束，发布任务失败!!!", level="Error")
        else:
            RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=2, )  # 修改发布状态
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=2, )  # 修改发布状态
            self.mylogway("发布流程结束，发布任务成功!!!", level="Info")

    def rollback_run(self):
        self.ssh = self.remote_server.get_sshclient()
        self.process_status.append("roll_back_Start")
        self.redis_cli.hmset(self._lockkey, {'lock_task': self.record_id, 'starttime': self._operatingtime,
                                             'pub_user': self.records_instance.pub_user,
                                             'pub_current_status': 'Start pub...',
                                             })
        self.redis_cli.hmset(self.record_id, {'error_detail': self.error_reason})  # 初始化，error_detail
        print("{0} Info: {1}  {2}开始回滚操作".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                self.remote_server, self._dstdir))
        RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=4)
        for myfunc in [self.stop_tomcat, self.rollback, self.start_tomcat]:
            if not self.have_error:
                myfunc()
                self.redis_cli.hmset(self._lockkey, {'pub_current_status': str(self.process_status)})  # 发布过程更新状态

        self.redis_cli.hmset(self._lockkey, {'pub_current_status': str(self.process_status)})
        self.redis_cli.delete(self._lockkey)
        if self.have_error:
            RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=-2)
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=-2)
            self.mylogway("回滚流程结束，回滚任务失败!!!")
        else:
            RecordOfjavajar.objects.filter(pk=self.records_instance.pk).update(pub_status=5)
            Fileupload.objects.filter(pk=self.fileupload_instace.pk).update(status=0)
            self.mylogway("回滚流程结束，回滚任务成功!!!", level='Info')

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
