# Generated by Django 2.0.1 on 2018-11-02 07:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('items', models.CharField(max_length=100)),
                ('project', models.CharField(default='', max_length=100)),
                ('project_cn', models.CharField(default='', max_length=100)),
                ('package_name', models.CharField(max_length=100, unique=True)),
                ('static_host', models.CharField(default='', max_length=200)),
                ('static_dir', models.CharField(default='', max_length=200)),
                ('file_save_base_dir', models.CharField(default='', max_length=200)),
                ('backup_file_dir', models.CharField(default='', max_length=200)),
                ('validate_user', models.CharField(default='', max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='RecordOfStatic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pub_time', models.DateTimeField(auto_now=True)),
                ('deployment_user', models.CharField(default='', max_length=50)),
                ('isthis_current', models.BooleanField(default=False)),
                ('return_user', models.CharField(default='', max_length=50)),
                ('upload_file', models.CharField(default='', max_length=50)),
                ('backuplist', models.CharField(default='', max_length=200)),
                ('newdir', models.CharField(default='', max_length=2000)),
                ('newfile', models.CharField(default='', max_length=4000)),
                ('ignore_new', models.BooleanField(default=False)),
                ('items', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontitems.ProjectInfo')),
            ],
        ),
    ]
