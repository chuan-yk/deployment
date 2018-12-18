import datetime

from django.utils import timezone
from django.test import TestCase

from .models import ProjectInfo, ServerInfo


class ProjectInfoTests(TestCase):

    def test_configs_equal(self):
        """测试type 1\2\3 类型配置文件一致"""
        for i in ProjectInfo.objects.filter(type=1):
            i_type2 = ProjectInfo.objects.get(items=i.items, platform=i.platform, type=2)
            self.assertEqual(i.output_configs(), i_type2.output_configs())
            i_type3 = ProjectInfo.objects.get(items=i.items, platform=i.platform, type=3)
            self.assertEqual(i.output_configs(), i_type3.output_configs())

    def test_configs_exist(self):
        """测试配置文件是否存在"""
        for i in ProjectInfo.objects.filter(type=1):
            the_config_list = i.output_configs()
            for j in the_config_list:
                self.assertIs(i.ipaddress.if_exist_file(j), True)
