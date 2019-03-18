import json
import paramiko
from django.db import models
from deployment.settings import key


# pkey=paramiko.RSAKey.from_private_key_file(key,password='******')
pkey = paramiko.RSAKey.from_private_key_file(key)


# Create your models here.
class ServerInfo(models.Model):
    ip = models.GenericIPAddressField(protocol='ipv4', unique=True, )
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=50, null=True, blank=True, default='root')
    platform = models.CharField(max_length=50, null=True, blank=True, help_text="所属平台")
    sys_type = models.IntegerField(default=1, null=True, blank=True, help_text="操作系统 1-linux，2-windows")
    purchase_time = models.DateField(null=True, blank=True, help_text="采购时间")
    region = models.CharField(max_length=20, null=True, blank=True, help_text="区域")
    third_cdn = models.IntegerField(default=0, null=True, blank=True, help_text="是否第三方CDN服务器， 0-否，1-是")
    note = models.CharField(max_length=100, default='', null=True, blank=True, help_text="备注")

    def __str__(self):
        return 'Server {}:{}'.format(self.ip, self.port)

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
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} "{1}" && echo True'.format(command_argv, path))
        # print('===debug ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False

    def if_exist_file(self, path):
        """check path is tag=(file or dir) , return True or false"""
        self.get_sshclient()
        command_argv = '-f'
        stdin, stdout, stderr = self.sshclient.exec_command('test {0} "{1}" && echo True'.format(command_argv, path))
        # print('===debug2 ', stdout.read(), stdout.read().decode())
        if stdout.read().decode() == 'True\n':
            return True
        else:
            return False


class ProjectInfo(models.Model):

    def __str__(self):
        return '{}:{}'.format(self.platform_cn, self.items)

    items = models.CharField(default='sobet', max_length=100, help_text='项目名称，如sobet，lottery，admin')
    platform = models.CharField(max_length=100, default='', help_text='平台名称，如MC\MD\CYQ')
    platform_cn = models.CharField(max_length=100, default='', help_text='中文名')
    package_name = models.CharField(max_length=100, default='', help_text='合法包名，允许字段为空')
    type = models.IntegerField(default='0', help_text='0 静态 1 全量war包 2 增量包 3 Jar包')
    dst_file_path = models.CharField(max_length=200, default='', help_text='文件发布路径')
    backup_file_dir = models.CharField(max_length=200, default='', help_text='备份根目录，如/backup/mc')
    validate_user = models.CharField(max_length=500, default='', help_text='有权限发布的用户/用户组， 暂未使用')
    ipaddress = models.ForeignKey(ServerInfo, on_delete=models.CASCADE, default='1', help_text='服务器IP地址')
    configs = models.CharField(max_length=3000, default='', help_text='项目配置文件信息')
    runuser = models.CharField(max_length=100, default='root', help_text='文件属主或启动用户')

    def input_configs(self, inputlist):
        """inputlist:传入字符串，写入configs 字段"""
        self.configs = json.dumps(inputlist)

    def output_configs(self):
        return json.loads(self.configs)
