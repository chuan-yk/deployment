#!/usr/bin/env python
import datetime,os
from .paramikoClient import *
from cmdb.models import ProjectInfo,ServerInfo
from fileupload.models import Fileupload



class DeploySet(object):

    def __init__(self,id,ptname,appname,filename,type):
       self.id = id
       self.ptname = ptname
       self.appname = appname
       self.filename = filename
       self.proobj = ProjectInfo.objects.filter(platform=ptname, items=appname,type=type)
       self.hostid = self.proobj.values('ipaddress_id').get()['ipaddress_id']
       self.ip = ServerInfo.objects.get(id=self.hostid).ip
       self.port = ServerInfo.objects.get(id=self.hostid).port
       self.apppconfath = os.path.join(self.proobj.get().dst_file_path,'/conf')
       self.filelocal_path = Fileupload.objects.filter(id=self.id).values('file').get()['file']
       #self.filelocal_path = "E:\\新建文件夹\\jsp-apii.zip"                                       #windos调试


    def jar(self,action):

        datenow = datetime.datetime.now().strftime('%Y%m%d-%H%M')
        #jarpath = os.path.join(self.proobj.get().dst_file_path,'webapps',self.appname,'lib')    #windos调试
        jarpath = '/usr/local/tomcat7.0_sobet/webapps/sobet/WEB-INF/lib/'
        destpath = '/tmp/{}/{}/{}'.format(self.ptname,self.appname,self.filename)
        path = os.path.join('/tmp/',self.ptname,self.appname)
        #path = '/tmp/mc/sobet'                                                                   #windos调试
        t = ParamikoClient(self.ip, self.port)
        t.sftp_push(self.filelocal_path,destpath)


        execResult = t.exec_commd('''
                       cp -r {apppath}/webapps/{appname} {bak_path}/{filename}_{date};
                       unzip -q {path}/{filenametxt} -d {path}/{filename};
                       cd {expath};
                       jar -uvf {jarpath}/{filename}.jar {filename};
                       rm -rf {path}
                        '''.format(path=path,bak_path=self.proobj.get().backup_file_dir,filenametxt=self.filename,
                                   filename=os.path.splitext(self.filename)[0],expath=path,
                                   appname=self.appname, date=datenow,jarpath=jarpath,
                                   apppath=self.proobj.get().dst_file_path))

        Resultdic = {'Title': '执行结果', 'Resultstdout': execResult[0][:-1].split('\n'),
                     'Resultstderr': execResult[1][0:-1].split('\n')}

        if execResult[2] != 0:
            return Resultdic

        if action == 1:
            print('开始重启应用')
            result = t.exec_commd('''
                    ps -ef|grep {Apppconfath}/conf|grep -v grep |grep -v tail|xargs kill -9;
                        {Apppconfath}/bin/startup.sh
                '''.format(Apppconfath=self.proobj.get().dst_file_path))

            print(result)
        return Resultdic


    def full(self):
        self.action

    def extra(self):
        pass
