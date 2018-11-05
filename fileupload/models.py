# encoding: utf-8
from django.db import models
from django.urls import reverse

class Fileupload(models.Model):
    """This is a small demo using just two fields. The slug field is really not
    necessary, but makes the code simpler. ImageField depends on PIL or
    pillow (where Pillow is easily installable in a virtualenv. If you have
    problems installing pillow, use a more generic FileField instead.

    """


    file = models.FileField(upload_to='')
    platform = models.CharField(max_length=100)
    app = models.CharField(max_length=100)
    bug_id = models.IntegerField(blank=True,null=True)
    description= models.CharField(max_length=500, blank=True)
    user = models.CharField(max_length=100, blank=True, null=True, unique=True)
    status = models.IntegerField(default=0,blank=True)
    create_date = models.DateTimeField( auto_now_add=True)
    slug = models.SlugField(max_length=50, blank=True)


    def __str__(self):

        return self.file.name


    @models.permalink
    def get_absolute_url(self):
        #return ('upload-new',kwargs={'pk': self.pk} )
        return reverse('upload-new', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        self.slug = self.file.name
        self.app = self.app
        self.platform = self.platform
        self.bug_id = self.bug_id
        self.description = self.description
        self.user =self.user

        super(Fileupload, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        """delete -- Remove to leave file."""
        self.file.delete(False)
        super(Fileupload, self).delete(*args, **kwargs)
