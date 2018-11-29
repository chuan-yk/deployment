#!/usr/bin/env python
import os,paramiko

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ParamikoClient(object):

    def __init__(self, host, port=22, user='root'):
        self.host = host
        self.user = user
        self.port = port
        self._sshkey = '{}\sshkey\id_rsa'.format(BASE_DIR)
        self._pkey = paramiko.RSAKey.from_private_key_file(self._sshkey)

    def exec_commd(self, cmd):
        t = paramiko.SSHClient()
        t.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        t.connect(hostname=self.host, username=self.user, port=self.port,pkey = self._pkey)
        stdin, stdout, stderr = t.exec_command(cmd)
        statuscod = stdout.channel
        status = statuscod.recv_exit_status()
        #res, err = stdout.read(), stderr.read()
        #result = res if res else err
        result = stdout.read(), stderr.read()
        return result[0].decode("utf-8"), result[1].decode("utf-8"),status


    def sftp_push(self, source, dest):

        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username='root', pkey=self._pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp.put(source,dest)
        except FileNotFoundError as e:
            print(FileNotFoundError,e)
            sftp.mkdir(os.path.split(dest)[0])
            sftp.put(source, dest)
            print('创建{}........done'.format(os.path.split(dest)[0]))
        transport.close()
        return 1
