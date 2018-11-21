#!/usr/bin/env python
import datetime
from .remote_run import *
from cmdb.models import ProjectInfo,ServerInfo



class DeploySet(object):

    def __init__(self,ptname,appname,filename,type):
       self.ptname = ptname
       self.appname = appname
       self.filename = filename
       self.type = type
       self.hostid =  ProjectInfo.objects.filter(platform=ptname,items=appname,)\
           .values('ipaddress_id').get()['ipaddress_id']
       self.ip = ServerInfo.objects.get(id=self.hostid).ip
       self.port = ServerInfo.objects.get(id=self.hostid).port
       self.proobj = ProjectInfo.objects.filter(platform=ptname,items=appname)




    def jar(self):

        datenow = datetime.datetime.now().strftime('%Y%m%d-%H%M')

        t = SSHManager(self.ip, self.port)
        t.ssh_connect()
        url = 'http://127.0.0.1/'
        path = '/tmp/'+self.appname

        execResult = t.ssh_exec_cmd('''wget -T 3 -q {url}{tmpname1} -P {path};
                       cp -r {apppath}/{appname} {bak_path}{filename}_{date};
                       unzip -q {path}/{tmpname1} -d {path}/{filename};
                       cd {expath};
                       jar -uvf {apppath}lib/{filename}.jar {filename};
                       rm -rf {path}/
                        '''.format(url=url, tmpname1='jstl.zip',path=path,bak_path=self.proobj.get().backup_file_dir,
                                   filename=os.path.splitext(self.filename)[0],expath=path,
                                   appname=self.appname, date=datenow,
                                   apppath=self.proobj.get().dst_file_path))

        Resultdic = {'Title': '执行结果', 'Resultstdout': execResult[0][:-1].split('\n'),
                     'Resultstderr': execResult[1][0:-1].split('\n')}

        if execResult[2] != 0:
            return Resultdic
        # if action == '1':
        #     print('restart')
        #     result = t.ssh_exec_cmd('''
        #         ps -ef|grep {dst_file_path}|grep -v grep |grep -v tail|xargs kill -9;
        #         {apppath}bin/startup.sh
        #         '''.format(apppath=prepareConfig(ptname, appname, appConf)))
        #     # print(result)

        return Resultdic


    def full(self):
        self.action

    def extra(self):
        pass
