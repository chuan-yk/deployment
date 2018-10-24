#!/usr/bin/env python
import paramiko,os,sys
from functools import wraps


class SSHManager(object):
    '''
        exec remote comm by host.conf
    '''
    def __init__(self,host,port=22,user='root'):
        self.host = host
        self.user = user
        self.port = port
        self._ssh = paramiko.SSHClient()
        self._sshkey = 'C:\\keys\\id_rsa_2048_shine'

    def __del__(self):

        if self._ssh:
            self._ssh.close()

    def ssh_connect(self):

        try:
            # 允许连接不在know_hosts文件中的主机
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # 指定本地的RSA私钥文件,如果建立密钥对时设置的有密码，password为设定的密码，如无不用指定password参数
            # pkey = paramiko.RSAKey.from_private_key_file('/home/super/.ssh/id_rsa', password='12345')
            #pkey = paramiko.RSAKey.from_private_key_file(r'E:\id_rsa_2048_shine')
            pkey = paramiko.RSAKey.from_private_key_file(self._sshkey)
            #连接服务器
            self._ssh.connect(hostname=self.host, port = self.port,username = self.user,pkey = pkey, timeout = 5)
        except Exception:
            raise RuntimeError ("ssh connected to [host:%s, usr:%s] failed" %
                               (self.host, self.user))

    def ssh_exec_cmd(self,cmd, path='~'):
        try:
            stdin, stdout, stderr = self._ssh.exec_command('cd ' + path + ';' + cmd)
            result = stdout.read(),stderr.read()
            statuscod = stdout.channel
            status = statuscod.recv_exit_status()

            #self._ssh.close()
        except Exception as e:
            raise RuntimeError('exec cmd  failed:[%s]' %e)

        print(result[0].decode("utf-8"),result[1].decode("utf-8"))
        return result[0].decode("utf-8"),result[1].decode("utf-8"),status

    def ssh_exec_shell(self,remotefile,pt,appname,filename=None):
        try:
            stdin, stdout, stderr = self._ssh.exec_command('{remotefile} {pt} {appname} {filename}'
                                               .format(remotefile=remotefile,pt=pt,appname=appname,filename=filename))
            result = stdout.read(), stderr.read()
            #self._ssh.close()

        except Exception as e:
            raise RuntimeError('ssh exec shell failed [%s]' % str(e))
        return result[0].decode("utf-8"),result[1].decode("utf-8")






