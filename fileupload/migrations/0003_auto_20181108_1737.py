# Generated by Django 2.0.8 on 2018-11-08 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fileupload', '0002_auto_20181108_1725'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileupload',
            name='app',
            field=models.CharField(default='-', max_length=100),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='bug_id',
            field=models.IntegerField(default='0'),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='create_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='description',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='file',
            field=models.FileField(null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='name',
            field=models.CharField(default='-', help_text='上传文件名', max_length=200),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='platform',
            field=models.CharField(default='-', max_length=100),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='slug',
            field=models.SlugField(blank=True),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='status',
            field=models.IntegerField(blank=True, default=0, help_text='-1 发布失败 0 未发布 1 正在发布 2 发布完成'),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='type',
            field=models.IntegerField(default='0', help_text='0 静态 1 全量war包 2 增量包 3 Jar包'),
        ),
        migrations.AddField(
            model_name='fileupload',
            name='user',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
