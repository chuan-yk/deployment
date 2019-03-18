from django.forms import ModelForm
from django import forms
from cmdb.models import ServerInfo
from .models import PrimaryDomain
from .models import DomainList


class ServerInfoForm(ModelForm):
    sys_choice = (
        ('1', 'Linux'),
        ('2', 'Windows'),
        ('3', '其他'),
    )
    cdn_choice = (
        ('0', '否'),
        ('1', '是'),
    )
    # sys_type = forms.TypedChoiceField(required=False, choices=sys_choice, widget=forms.RadioSelect)
    sys_type = forms.ChoiceField(choices=sys_choice)
    # third_cdn = forms.TypedChoiceField(required=False, choices=cdn_choice, widget=forms.RadioSelect)
    third_cdn = forms.ChoiceField(choices=cdn_choice)

    class Meta:
        model = ServerInfo
        fields = '__all__'
        widgets = {'purchase_time': forms.DateInput(attrs={'type': 'date'})}  # 修改template input字段类型


class PrimaryDomainForm(ModelForm):
    status_choice = (
        ('0', '未使用'),
        ('1', '使用中'),
        ('2', '被墙'),
        ('3', '停用'),
    )
    status = forms.ChoiceField(choices=status_choice)

    class Meta:
        model = PrimaryDomain
        fields = '__all__'
        widgets = {'start_time': forms.DateInput(attrs={'type': 'date'}),
                   'expire_time': forms.DateInput(attrs={'type': 'date'}), }  # 修改template input字段类型


class DomainListForm(ModelForm):
    cdn_choice = (
        ('0', '否'),
        ('1', '是'),
    )
    encryption_choice = (
        ('0', '未使用'),
        ('1', '使用中'),
        ('2', '即将过期'),
        ('3', '已过期'),
        ('4', '连接不通'),
    )
    cdn = forms.ChoiceField(choices=cdn_choice)

    class Meta:
        model = DomainList
        fields = ['domain', 'platform', 'cdn', 'server', 'port', 'note']
        required = ['domain', 'cdn', 'port', ]
        widgets = {'update_time': forms.DateInput(attrs={'type': 'date'}),
                   'start_time': forms.DateInput(attrs={'type': 'date'}),
                   'expire_time': forms.DateInput(attrs={'type': 'date'}), }  # 修改template input字段类型


class DomainListAddForm(ModelForm):
    cdn_choice = (
        ('0', '否'),
        ('1', '是'),
    )
    cdn = forms.ChoiceField(choices=cdn_choice)

    class Meta:
        model = DomainList
        fields = ['domain', 'platform', 'cdn', 'port', 'note']
        widgets = {'update_time': forms.DateInput(attrs={'type': 'date'}),
                   'start_time': forms.DateInput(attrs={'type': 'date'}),
                   'expire_time': forms.DateInput(attrs={'type': 'date'}), }  # 修改template input字段类型
