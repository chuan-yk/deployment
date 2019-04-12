import threading
import xlrd
import logging
from django.db.models import Q
from django.shortcuts import render, HttpResponse, redirect, HttpResponseRedirect
from django.shortcuts import get_list_or_404, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .domain_tools import manual_execute
from cmdb.models import ServerInfo
from .models import PrimaryDomain, DomainList
from .forms import ServerInfoForm, PrimaryDomainForm, DomainListForm, DomainListAddForm
from .domain_tools import init_server_info, init_primary_domain, init_domain
from .domain_tools import ssl_certificate_info, get_remote_addr, get_dns_resolver, analysis_primary_domain
from .domain_tools import domain_add_new_relate
from .domain_tools import multiple_flush


loger = logging.getLogger('runlog')


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
            attr = dict()
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
    query_conditions = [Q(id__gt=0), ~Q(encryption=0)]
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
    return render(request, 'domains/domain_ssl_index.html', content)


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
                try:
                    add_result = domain_add_new_relate(new_form)  # 新增过程中默认解析单个域名DNS，HTTPS证书信息
                    if add_result['status']:
                        return redirect('/domain/list/', messages.success(request, add_result['msg'], 'alert-success'))
                    else:
                        return redirect('/domain/list/',
                                        messages.error(request, '更新域名失败, {}'.format(add_result['msg']), 'alert-danger'))
                except Exception as e:
                    return redirect('/domain/list/', messages.error(request, '更新域名错误, {}'.format(e), 'alert-danger'))
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
    if pk == '0':
        domains = DomainList.objects.filter(Q(been_deleted__exact=False))
        threading_task = threading.Thread(target=multiple_flush, args=(domains,))  # 多线程执行发布过程
        threading_task.start()
        print("domain_ssl_flush开始刷新全部域名信息")
    else:
        domain = get_object_or_404(DomainList, pk=pk)
        print("domain_ssl_flush开始刷新域名{}信息".format(domain.domain))
        flush_result = domain_add_new_relate(domain)
        if flush_result['status']:
            messages.success(request, flush_result['msg'], 'alert-success')
        else:
            messages.error(request, flush_result['msg'], 'alert-danger')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    messages.info(request, '刷新任务执行中', 'alert-success')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def domains_import(request):
    """批量导入"""
    if request.method == 'POST':
        try:
            the_file = request.FILES.get('thefile')
            wb = xlrd.open_workbook(filename=None, file_contents=the_file.read(), formatting_info=True)  # xls文件
            table = wb.sheets()[0]
            new_list = [i for i in range(table.nrows-1)]
            for i in range(1, table.nrows):
                new_list[i-2] = DomainList(domain=str(table.cell_value(i, 0).strip()),
                                           port=int(table.cell_value(i, 1)) or 80,
                                           note=table.cell_value(i, 4),
                                           cdn=table.cell_value(i, 5),
                                           platform=str(table.cell_value(i, 6).strip())
                                           )

            loger.debug("读取上传表格完成，{}".format(new_list))
            multiple_flush(new_list)
            # 用完记得删除
            wb.release_resources()
            del wb
        except Exception as e:
            messages.error(request, str(e), 'alert-danger')
            loger.error('request 上传文件导入失败， 错误原因{}'.format(str(e)))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        return render(request, 'domains/upload.html')
