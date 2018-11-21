from django.db import models
from django.utils import timezone

from cmdb.models import ServerInfo, ProjectInfo


class RecordOfStatic(models.Model):
    items = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)  # 项目
    record_id = models.CharField(max_length=50, default='', unique=True)  # 发布任务/记录ID，约定格式 mc_sobet_文件type_文件ID
    pub_filemd5sum = models.CharField(max_length=50, default='')  # MD5 值
    pub_time = models.DateTimeField(auto_now=True, null=True)  # 发布时间
    pub_status = models.IntegerField(default='0', )  # 发布状态:-1 发布失败 0 未发布 1 正在发布 2 发布完成 3 解压查看详情 4 回滚中 5回滚OK -2 回滚失败，
    pub_user = models.CharField(max_length=50, default='')  # 发布用户
    return_user = models.CharField(max_length=50, default='')  # 回滚改版本用户
    backuplist = models.CharField(max_length=200, default='')  # 备份子目录
    backupsavedir = models.CharField(max_length=200, default='')  # 备份所在目录
    newdir = models.CharField(max_length=2000, default='')  # 本次发布新增文件列表
    newfile = models.CharField(max_length=4000, default='')  # 本次发布新增文件夹列表
    ignore_new = models.BooleanField(default=False)  # 是否忽略新增文件（True: 无论是否新增均进行发布）

    def __str__(self):
        return 'Record for {}, pub_time:{}'.format(self.items, self.pub_time)

    def onlyone_current(self):
        pass
