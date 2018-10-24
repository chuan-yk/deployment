from django.db import models
from django.utils import timezone

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
    # ssh_server = models.IPAddressField(default='')
    # ssh_port = models.IntegerField(default=22)

    # def connect_sshserver(self, pk):
    #     pass

class RecordOfStatic(models.Model):

    items = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)
    pub_time = models.DateTimeField(auto_now=True)
    deployment_user = models.CharField(max_length=50, default='')
    isthis_current = models.BooleanField(default=False)
    #return_status = models.IntegerField(default = 0)
    return_user = models.CharField(max_length=50, default='')
    upload_file = models.CharField(max_length=50, default='')
    backuplist = models.CharField(max_length=200, default='')
    newdir = models.CharField(max_length=2000, default='')
    newfile = models.CharField(max_length=4000, default='')
    ignore_new = models.BooleanField(default=False)
    def __str__(self):
        return 'Record for {}, pub_time:{}'.format(self.items, self.pub_time)
    def onlyone_current(self):
        pass


