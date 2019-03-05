import json

from django.db import models
from cmdb.models import ServerInfo


class PrimaryDomain(models.Model):
    primary = models.CharField(max_length=100, null=False, blank=False, help_text="主域名")
    platform = models.CharField(max_length=10, null=True, blank=True, default='', help_text="所属平台")
    status = models.IntegerField(default=0, help_text="使用状态： 0-未使用， 1-使用中， 2-被墙， 3-停用")
    start_time = models.DateField(null=True, blank=True, help_text='域名采购时间')
    expire_time = models.DateField(null=True, blank=True, help_text='域名到期时间')
    note = models.CharField(max_length=100, default='', null=True, blank=True, help_text="备注")


class DomainList(models.Model):
    domain = models.CharField(max_length=100, default='', help_text="域名")
    primary_domain = models.ForeignKey(PrimaryDomain, related_name='primary_set', on_delete=models.CASCADE, null=False,
                                       help_text='主域')
    server = models.ForeignKey(ServerInfo, related_name='server_set', on_delete=models.CASCADE, null=False,
                               help_text='解析服务器地址')
    port = models.IntegerField(default=80, help_text="使用端口，默认80, https默认443, 特殊情况选用其他加密端口")
    encryption = models.IntegerField(default=0, help_text="HTTPS使用状态： 0-未使用， 1-使用中， 2-即将过期， 3-已过期")
    multi_cr = models.IntegerField(default=0, help_text="是否使用多域名证书，0-否， 1-是")
    multi_list = models.CharField(max_length=500, null=True, blank=True, help_text="同一证书域名")
    start_time = models.DateField(null=True, blank=True, help_text='域名采购时间')
    expire_time = models.DateField(null=True, blank=True, help_text='域名到期时间')
    note = models.CharField(max_length=100, default='', null=True, blank=True, help_text="备注")

    def get_multi_list(self):
        return json.loads(self.multi_list)

    def set_multi_list(self, inputlist):
        """inputlist:传入字符串，写入multi_list 字段"""
        self.configs = json.dumps(inputlist)

