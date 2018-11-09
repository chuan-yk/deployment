# encoding: utf-8
from django.db import models
from django.urls import reverse

class Fileupload(models.Model):
    """This is a small demo using just two fields. The slug field is really not
    necessary, but makes the code simpler. ImageField depends on PIL or
    pillow (where Pillow is easily installable in a virtualenv. If you have
    problems installing pillow, use a more generic FileField instead.

    """
    file = models.FileField(upload_to='', null=True)
    platform = models.CharField(default='-', max_length=100)
    name = models.CharField(max_length=200, default='-', help_text='上传文件名')
    type = models.IntegerField(default='0', help_text='0 静态 1 全量war包 2 增量包 3 Jar包')
    app = models.CharField(max_length=100, default='-')
    bug_id = models.IntegerField(default='0',)
    description= models.CharField(max_length=500, blank=True)
    user = models.CharField(max_length=100, blank=True, null=True)
    status = models.IntegerField(default=0, blank=True, help_text='-1 发布失败 0 未发布 1 正在发布 2 发布完成')
    create_date = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=50, blank=True)
    pubuser = models.CharField(max_length=100, default=None, null=True)


    def __str__(self):
        return self.file.name


    @models.permalink
    def get_absolute_url(self):
        #return ('upload-new',kwargs={'pk': self.pk} )
        return reverse('upload-new', kwargs={'pk': self.pk})

    def save(self,*args, **kwargs):
        self.slug = self.file.name
        self.app = self.app
        self.platform = self.platform
        self.name = self.file.name
        self.bug_id = self.bug_id
        self.description = self.description
        self.user = self.user
        super(Fileupload, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        """delete -- Remove to leave file."""
        self.file.delete(False)
        super(Fileupload, self).delete(*args, **kwargs)
