# Generated by Django 2.0.8 on 2018-11-14 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontitems', '0004_recordofstatic_platform'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordofstatic',
            name='pub_time',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
