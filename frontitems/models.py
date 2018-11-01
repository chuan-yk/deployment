from django.db import models
from django.utils import timezone

from cmdb.models import ServerInfo


class ProjectInfo(models.Model):
    def __str__(self):
        return '{} : {}'.format(self.project,   self.items)
    items = models.CharField(max_length=100)    #lottery\sobet\lottery_m\sport
    project = models.CharField(max_length=100, default='')  #mc\md\cyq
    project_cn = models.CharField(max_length=100, default='')  #mc\md\cyq cn
    package_name = models.CharField(max_length=100, unique=True)
    static_host = models.CharField(max_length=200,default='')
    static_dir = models.CharField(max_length=200, default='')
    file_save_base_dir = models.CharField(max_length=200,default='')
    backup_file_dir = models.CharField(max_length=200,default='')
    validate_user = models.CharField(max_length=500,default='')
    server_ipaddress = models.ForeignKey(ServerInfo, on_delete=models.CASCADE)


class RecordOfStatic(models.Model):

    items = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)        # 项目
    pub_time = models.DateTimeField(auto_now=True)                          # 发布时间
    upload_user = models.CharField(max_length=50, default='')               # 上传用户
    wait_pub = models.BooleanField(default=True)                            # 等待发布状态
    dev_note = models.CharField(max_length=1000, default='')                # 开发人员的备注
    pub_user = models.CharField(max_length=50, default='')                  # 发布用户
    isthis_current = models.BooleanField(default=False)                     # 是否为当前最新版本
    return_user = models.CharField(max_length=50, default='')               # 回滚改版本用户
    upload_file = models.CharField(max_length=50, default='')               # 上传文件保存地址
    backuplist = models.CharField(max_length=200, default='')               # 备份所在目录
    newdir = models.CharField(max_length=2000, default='')                  # 本次发布新增文件列表
    newfile = models.CharField(max_length=4000, default='')                 # 本次发布新增文件夹列表
    ignore_new = models.BooleanField(default=False)                         # 是否忽略新增文件（True: 无论是否新增均进行发布）
    def __str__(self):
        return 'Record for {}, pub_time:{}'.format(self.items, self.pub_time)
    def onlyone_current(self):
        pass


