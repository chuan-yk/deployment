from django.test import TestCase
import paramiko

from .remotepubstatic import RemoteReplaceWorker


# class for debug
class Rserver(object):
    key = "sshkey\\id_rsa"
    pkey = paramiko.RSAKey.from_private_key_file(key)

    def __init__(self, ip, port, username):
        self.ip = ip
        self.port = port
        self.username = username

    def connect(self):
        try:
            if not self.transport.is_alive():
                self.transport = paramiko.Transport((self.ip, self.port))
                self.transport.connect(username=self.username, pkey=self.pkey)
        except:
            self.transport = paramiko.Transport((self.ip, self.port))
            self.transport.connect(username=self.username, pkey=self.pkey)

    def get_sshclient(self):
        # print('debug,  ==', self.ip, self.port,self.username)
        try:
            # Avoid duplicate links
            if self.sshclient.get_transport().is_active():
                return self.sshclient
        except AttributeError:
            self.connect()
            self.sshclient = paramiko.SSHClient()
            self.sshclient._transport = self.transport
            return self.sshclient
        except Exception as e:
            print(e)
            return None

    def sshclient_close(self):
        try:
            self.sshclient.close()
        except:
            pass

    def get_xftpclient(self):
        self.xftpclient_close()
        try:
            self.connect()
            self.sftpclient = paramiko.SFTPClient.from_transport(self.transport)
            return self.sftpclient
        except Exception as e:
            print(e)
            return None

    def xftpclient_close(self):
        try:
            self.sftpclient.close()
        except:
            pass

    def if_exist_dir(self, path):
        """check path is tag=(file or dir) , return True or false"""
        self.get_sshclient()
        command_argv = '-d'
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} {1} && echo True'.format(command_argv, path))
        # print('===debug ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False

    def if_exist_file(self, path):
        """check path is tag=(file or dir) , return True or false"""
        self.get_sshclient()
        command_argv = '-f'
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} {1} && echo True'.format(command_argv, path))
        # print('===debug2 ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False


if __name__ == "__main__":
    import os

    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "D:\\deployment\\deployment\\deployment.settings.py")
    # sys.path.extend(['D:\\deployment', 'D:\\Program Files\\PyCharm 2018.1.4\\helpers\\pycharm',
    #                  'D:\\Program Files\\PyCharm 2018.1.4\\helpers\\pydev'])

    serverinfo_150 = Rserver('192.168.159.150', 22, 'root')
    print(serverinfo_150)
    dst = '/var/www/html'
    fromfile1 = "/tmp/sobet.zip"
    platfrom = 'mc'
    projectname1 = 'sobet'
    backupdir = '/data/release/mc'
    rmt_tasker = RemoteReplaceWorker(serverinfo_150, dst, fromfile1, platfrom, projectname1, backupdir)
    rmt_tasker.pip_run()
