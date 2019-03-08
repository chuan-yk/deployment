from django.db.models import Q
from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .domain_tools import manual_execute
from cmdb.models import ServerInfo
from .models import PrimaryDomain, DomainList
from .forms import ServerInfoForm, PrimaryDomainForm, DomainListForm, DomainListAddForm
from .domain_tools import ssl_certificate_info, get_remote_addr, get_dns_resolver, analysis_primary_domain
from .domain_tools import domain_add_new_relate


def tmp_analysis(request):
    # 临时解决办法
    file = request.GET.get('file')
    print(file)
    try:
        with open(file, 'r') as f:
            f_lines = f.readlines()
        m_list = []
        for i in f_lines:
            print('check domain', i)
            m_list.append(i.strip('\n').strip())
        print(m_list)
        print('get f_lines ok ----------------------')
        manual_execute(m_list)
        return HttpResponse('success !')
    except Exception as e:
        return HttpResponse('fail ? {}'.format(str(e)))


@login_required
def node_index(request):
    # 解析节点管理
    query_conditions = [Q(id__gt=0), ]
    content = {'q_ip': '', 'q_note': '', }
    if request.GET.get('q_ip'):
        q_ip = request.GET.get('q_ip')
        query_conditions.append(Q(ip__contains=q_ip))
        content['q_ip'] = q_ip
    if request.GET.get('q_note'):
        q_note = request.GET.get('q_note')
        query_conditions.append(Q(note__contains=q_note))
        content['q_note'] = q_note
    content['nodes'] = ServerInfo.objects.filter(*query_conditions)
    return render(request, 'domains/node_index.html', content)


@login_required
def node_edit(request, pk):
    the_server = ServerInfo.objects.get(pk=pk)
    if request.POST:
        try:
            form = ServerInfoForm(request.POST, instance=the_server)
            if form.is_valid():
                if form.save():
                    return redirect('/domain/node', messages.success(request, '更新IP成功', 'alert-success'))
                else:
                    return redirect('/domain/node', messages.error(request, '更新IP失败', 'alert-danger'))
            else:
                return redirect('/domain/node', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('node_edit , POST, save form error', e)
        return redirect('/domain/node', messages.error(request, '内部错误', 'alert-danger'))
    else:
        form = ServerInfoForm(instance=the_server)
        return render(request, 'domains/node_edit.html', {'form': form})


@login_required
def node_add(request):
    if request.POST:
        try:
            form = ServerInfoForm(request.POST)
            if form.is_valid():
                if form.save():
                    return redirect('/domain/node', messages.success(request, '更新IP成功', 'alert-success'))
                else:
                    return redirect('/domain/node', messages.error(request, '更新IP失败', 'alert-danger'))
            else:
                return redirect('/domain/node', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('node_add , POST, save form error', e)
        return redirect('/domain/node', messages.error(request, '内部错误', 'alert-danger'))
    else:
        form = ServerInfoForm()
        return render(request, 'domains/node_edit.html', {'form': form})


@login_required
def node_import(request):
    return HttpResponse('test')


@login_required
def node_export(request):
    return HttpResponse('test')


@login_required
def primary(request):  # q_domain
    # 主域名管理列表
    query_conditions = [Q(id__gt=0), ]
    content = {'q_domain': '', 'q_note': '', }
    if request.GET.get('q_domain'):
        q_domain = request.GET.get('q_domain')
        query_conditions.append(Q(primary__contains=q_domain))
        content['q_domain'] = q_domain
    if request.GET.get('q_note'):
        q_note = request.GET.get('q_note')
        query_conditions.append(Q(note__contains=q_note))
        content['q_note'] = q_note
    content['domains'] = PrimaryDomain.objects.filter(*query_conditions)
    return render(request, 'domains/primary_index.html', content)


@login_required
def pry_import(request):
    return HttpResponse('test')


@login_required
def pry_export(request):
    return HttpResponse('test')


@login_required
def primary_edit(request, pk):
    the_primary = PrimaryDomain.objects.get(pk=pk)
    if request.POST:
        try:
            form = PrimaryDomainForm(request.POST, instance=the_primary)
            if form.is_valid():
                if form.save():
                    return redirect('/domain/primarydomain', messages.success(request, '更新IP成功', 'alert-success'))
                else:
                    return redirect('/domain/primarydomain', messages.error(request, '更新IP失败', 'alert-danger'))
            else:
                return redirect('/domain/primarydomain', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('node_edit , POST, save form error', e)
        return redirect('/domain/primarydomain', messages.error(request, '内部错误', 'alert-danger'))
    else:
        form = PrimaryDomainForm(instance=the_primary)
        return render(request, 'domains/primary_edit.html', {'form': form})


@login_required
def pry_add(request):
    if request.POST:
        try:
            form = PrimaryDomainForm(request.POST, )
            if form.is_valid():
                if form.save():
                    return redirect('/domain/primarydomain', messages.success(request, '更新IP成功', 'alert-success'))
                else:
                    return redirect('/domain/primarydomain', messages.error(request, '更新IP失败', 'alert-danger'))
            else:
                return redirect('/domain/primarydomain', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('node_edit , POST, save form error', e)
        return redirect('/domain/primarydomain', messages.error(request, '内部错误', 'alert-danger'))
    else:
        form = PrimaryDomainForm()
        return render(request, 'domains/primary_edit.html', {'form': form})


@login_required
def domain_list(request):
    query_conditions = [Q(id__gt=0), ]
    content = {'q_ip': '', 'q_note': '', 'q_domain': ''}
    if request.GET.get('q_ip'):
        q_ip = request.GET.get('q_ip')
        query_conditions.append(Q(server__ip__contains=q_ip))
        content['q_ip'] = q_ip
    if request.GET.get('q_domain'):
        q_domain = request.GET.get('q_domain')
        query_conditions.append(Q(domain__contains=q_domain))
        content['q_domain'] = q_domain
    if request.GET.get('q_note'):
        q_note = request.GET.get('q_note')
        query_conditions.append(Q(note__contains=q_note))
        content['q_note'] = q_note

    content['domains'] = DomainList.objects.filter(*query_conditions)
    return render(request, 'domains/domain_list_index.html', content)


@login_required
def domain_list_ssl(request):
    return HttpResponse('test')


@login_required
def domain_edit(request, pk):
    the_doamin = DomainList.objects.get(pk=pk)
    if request.POST:
        try:
            form = DomainListForm(request.POST, instance=the_doamin)
            if form.is_valid():
                if form.save():
                    return redirect('/domain/list/', messages.success(request, '更新域名成功', 'alert-success'))
                else:
                    return redirect('/domain/list/', messages.error(request, '更新域名失败', 'alert-danger'))
            else:
                return redirect('/domain/list/', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('domain_edit , POST, save form error', e)
        return redirect('/domain/list/', messages.error(request, '内部错误', 'alert-danger'))
    else:
        domain_ssl_info = DomainList.objects.get(pk=pk)
        try:
            multi_list = str(domain_ssl_info.get_multi_list())
        except:
            multi_list = ''
        form = DomainListForm(instance=the_doamin)
        return render(request, 'domains/domain_edit.html',
                      {'form': form, 'domain_ssl_info': domain_ssl_info, 'multi_list': multi_list})


@login_required
def domain_add(request):
    if request.POST:
        try:
            form = DomainListAddForm(request.POST)
            if form.is_valid():
                new_form = form.save(commit=False)
                new_form = domain_add_new_relate(new_form)
                try:
                    new_form.save()
                    return redirect('/domain/list/', messages.success(request, '更新域名成功', 'alert-success'))
                except Exception as e:
                    return redirect('/domain/list/', messages.error(request, '更新域名失败, {}'.format(e), 'alert-danger'))
            else:
                return redirect('/domain/list/', messages.error(request, '输入数据格式不正确', 'alert-danger'))
        except Exception as e:
            print('domain_add , POST, save form error', e)
        return redirect('/domain/list/', messages.error(request, '内部错误', 'alert-danger'))
    else:
        form = DomainListAddForm()
        return render(request, 'domains/domain_add.html', {'form': form, })


@login_required
def domain_ssl_flush(request, pk):
    return HttpResponse('test')
