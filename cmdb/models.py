from django.db import models
import paramiko

key = "sshkey\\id_rsa"
#key = "~/.ssh/id_rsa"
# pkey=paramiko.RSAKey.from_private_key_file(key,password='******')
pkey = paramiko.RSAKey.from_private_key_file(key)


# Create your models here.
class ServerInfo(models.Model):
    ip = models.GenericIPAddressField(protocol='ipv4')
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=50, default='root')

    def __str__(self):
        return 'Info {}:{}'.format(self.ip, self.port)

    def connect(self):
        try:
            if not self.transport.is_alive():
                self.transport = paramiko.Transport((self.ip, self.port))
                self.transport.connect(username=self.username, pkey=pkey)
        except:
            self.transport = paramiko.Transport((self.ip, self.port))
            self.transport.connect(username=self.username, pkey=pkey)

    def get_sshclient(self):
        # print('debug,  ==', self.ip, self.port,self.username)
        try:
            # Avoid duplicate links
            if self.sshclient.get_transport().is_active():
                return self.sshclient
        except AttributeError :
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

    def if_exist_dir(self,path):
        """check path is tag=(file or dir) , return True or false"""
        self.get_sshclient()
        command_argv = '-d'
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} "{1}" && echo True'.format(command_argv, path))
        #print('===debug ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False

    def if_exist_file(self,path):
        """check path is tag=(file or dir) , return True or false"""
        self.get_sshclient()
        command_argv = '-f'
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} "{1}" && echo True'.format(command_argv, path))
        #print('===debug2 ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False


