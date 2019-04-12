import socket
import dns.resolver
import logging
# import os, django
import requests
import ssl
import datetime
import time
from django.db.models import Q
from cmdb.models import ServerInfo
from domains.models import PrimaryDomain, DomainList


# 查询DNS解析
def get_dns_resolver(domain):
    # 通过DNS查询，返回格式['查询域名', '当前解析地址', '解析地址IP列表', 'CNAME地址列表']
    res = dns.resolver.Resolver()
    ip_list = []
    cname_list = []
    ip_address = '0.0.0.0'
    try:
        query_result = res.query(domain)
        for i in query_result.response.answer:
            for j in i:
                if j.rdtype == 1:
                    ip_list.append(j.address)
                if j.rdtype == 5:
                    cname_list.append(str(j.target).strip('.'))
                ip_address = str(j)
        return [domain, ip_address, ip_list, cname_list]
    except dns.resolver.Timeout:
        print('{0} check_domain_dns_records by query DNS server , query DNS time out'.format(domain))
        return [domain, ip_address, ip_list, cname_list]
    except Exception as err:
        print(str('{} check_domain_dns_records by query DNS server ,'.format(domain)) + str(err))
        return [domain, ip_address, ip_list, cname_list]


# 查询解析地址，socket方式
def get_remote_addr(domain):
    # 约定返回数据格式['查询域名', '当前解析地址', '解析地址IP列表', 'CNAME地址列表']
    print('get_remote_addr check on {}'.format(domain))
    try:
        result = socket.gethostbyname_ex(domain)
        return [domain, result[2][0], result[2], result[1], ]
    except IndexError as err:
        print('get_remote_addr IndexError', err)
        return [domain, '0.0.0.0', [], [], ]
    except socket.gaierror as err:
        print('get_remote_addr err:', err)
        return [domain, '0.0.0.0', [], [], ]
    except ConnectionResetError as err:
        print('get_remote_addr connect err:', err)
        return [domain, '0.0.0.0', [], [], ]


# 解析一级域名
def analysis_primary_domain(domain_name):
    fragmentation_list = domain_name.split('.')
    the_primary_domain = '.'.join(fragmentation_list[-2:])
    return the_primary_domain


# 初始化PrimaryDomain记录信息
def init_primary_domain(primary, **attr):
    the_primary, created = PrimaryDomain.objects.get_or_create(primary=primary,
                                                               defaults={'platform': attr.get('platform', None),
                                                                         'filing': attr.get('filing', False),
                                                                         'status': attr.get('status', 0),
                                                                         'start_time': attr.get('start_time', None),
                                                                         'expire_time': attr.get('expire_time', None),
                                                                         'note': attr.get('note', '')
                                                                         })
    return the_primary, created


# 初始化ServerInfo信息记录
def init_server_info(ip, query_region=False, **attr):
    if query_region:  # 自动解析IP所属地
        headers = {'User-Agent': 'curl/7.62.0', }
        url = 'https://ip.cn/?ip={}'.format(ip)
        r = requests.get(url, headers=headers)
        try:
            attr['region'] = r.content.decode().strip().split('来自:')[1].strip()
        except IndexError:
            print("Warnning init_server_info 自动解析IP所属地， 请求IP.CN 响应异常")
    the_server, created = ServerInfo.objects.get_or_create(ip=ip, defaults={'port': attr.get('port', 22),
                                                                            'username': attr.get('username', 'root'),
                                                                            'platform': attr.get('platform'),
                                                                            'sys_type': attr.get('sys_type', 1),
                                                                            'purchase_time': attr.get('purchase_time',
                                                                                                      None),
                                                                            'region': attr.get('region'),
                                                                            'third_cdn': attr.get('third_cdn', 0),
                                                                            'note': attr.get('note')})
    return the_server, created


# 初始化Domain records信息记录(指定解析IP)
def init_domain(domain, server_id, port, analysis=False, **attr):
    primary_name = analysis_primary_domain(domain)
    tmp_attr = dict()
    primary_domain, created = init_primary_domain(primary_name, **tmp_attr)
    attr['primary_domain'] = primary_domain
    if analysis:  # 自动解析域名证书
        ip = ServerInfo.objects.get(pk=server_id).ip
        info = ssl_certificate_info(domain, ip, port)
        print("debug init_domain分析域名{} 结果为{}".format(domain, info))
        attr['encryption'] = info.get('status')
        if attr['encryption'] == 1:
            attr['start_time'] = info.get('start_time').date()
            attr['expire_time'] = info.get('expire_time').date()
        if info['multi_name']:
            attr['multi_cr'] = 1
            attr['multi_list'] = info.get('multi_name')
    the_domain, created = DomainList.objects.get_or_create(domain=domain, server_id=server_id, port=port,
                                                           defaults={'primary_domain': attr.get('primary_domain'), })
    # 已有记录更新最新值或保持不变
    the_domain.platform = attr.get('platform') or the_domain.platform
    the_domain.cdn = attr.get('cdn') or the_domain.cdn
    the_domain.note = attr.get('note') or the_domain.note
    the_domain.encryption = attr.get('encryption') or the_domain.encryption
    the_domain.multi_cr = attr.get('multi_cr') or the_domain.multi_cr
    the_domain.multi_list = attr.get('multi_list') or the_domain.multi_list
    the_domain.start_time = attr.get('start_time') or the_domain.start_time
    the_domain.expire_time = attr.get('expire_time') or the_domain.expire_time
    the_domain.save()
    print("Debug init_domain: {}:{} on IP {} OK".format(domain, port, ip))
    return the_domain, created


# ssl 证书解析
# def ssl_certificate_info(domain, port=443):
def ssl_certificate_info(domain, ip, port=443):
    """
    传入域名和指定解析IP,返回证书信息
    约定格式: {
        ‘status’： 0-未使用|1-使用中|2-连接不通或被墙|3-已过期|4-即将过期"，
        ‘start_time’: '证书生效时间',
        'expire_time': '证书过期时间'',
        ‘multi_name’: '共用证书的域名list' }
    """
    # logdft('ssl_certificate_info check on {} {}， IP： {}'.format(domain, port, ip))
    info = {'status': 0, 'start_time': '', 'expire_time': '', 'multi_name': [], }
    ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'
    try:
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=domain, )
        conn.settimeout(3.0)  # 超时时间3秒
        print("debug, ssl_certificate_info analysis {} on IP {}, ".format(domain, ip, ))
        conn.connect((ip, port))
        ssl_info = conn.getpeercert()
        info['status'] = 1
        info['expire_time'] = datetime.datetime.strptime(ssl_info['notAfter'], ssl_date_fmt)
        info['start_time'] = datetime.datetime.strptime(ssl_info['notBefore'], ssl_date_fmt)
        for i in ssl_info['subjectAltName']:
            info['multi_name'].append(i[1])
        # 过期天数计算
        effective_days = (info['expire_time'] - datetime.datetime.today()).days
        if effective_days < 14:  # 即将过期，少于14天
            info['status'] = 4
        return info
    # Name or service not known
    except socket.gaierror:
        return info
    # 证书不匹配
    except ssl.CertificateError as e:
        print('ssl_certificate_info check {}:{}'.format(domain, port), e)
        return info
    # 连接拒绝
    except ConnectionRefusedError:
        print('{} {} ConnectionRefusedError, pass '.format(domain, port))
        return info
    # ssl.SSLError, 证书过期
    except ssl.SSLError:
        info['status'] = 3
        print('{} {} ssl.SSLError, expired , pass '.format(domain, port))
        return info
    # ConnectionResetError , 被墙或被强其它情况导致连接不通
    except ConnectionResetError:
        info['status'] = 2
        print('Error {} {} ConnectionResetError , Reset connect , pass '.format(domain, port))
        return info
    # socket.timeout: timed out, 连接不通等待时间过长
    except socket.timeout:
        info['status'] = 2
        print('Error {} {} socket.timeout: timed out , pass '.format(domain, port))
        return info
    except OSError:
        info['status'] = 2
        print('Error {} {} OSError:  overpass '.format(domain, port))
        return info
    except Exception as e:
        info['status'] = 2
        print('Error {} {} unknown Error:  {} '.format(domain, port, e))
        return info
    finally:
        if conn:
            conn.close()


# 新增域名自动解析|刷新域名信息
def domain_add_new_relate(m):
    print("start Add domain: {}".format(m.domain))
    argv = {'platform': m.platform, 'cdn': m.cdn, 'note': m.note, }
    # 初始化IP 信息
    ips = get_remote_addr(m.domain)[2]
    print("relate domain: {}, IPS= {}".format(m.domain, ips))
    if len(ips) == 0:
        return {'status': False, 'records': 0, "msg": "无法解析域名", }
    # 解析域名
    domain_add_list = []
    for ip in ips:
        print("debug domain_add_new_relate, current IP:", ip)
        # 初始化Server数据库
        # i_server, created = init_server_info(ip, query_region=False, **argv)
        i_server, created = init_server_info(ip, query_region=True, **argv)
        the_domain, created = init_domain(m.domain, i_server.id, m.port, analysis=True, **argv)
        domain_add_list.append(the_domain)
        print("debug domain_add_list=", domain_add_list)
    # 自动删除过期|旧的解析地址
    auto_del_count = 0
    for d in DomainList.objects.filter(Q(domain__exact=m.domain), Q(port__exact=m.port)):
        if d.server.ip not in ips:
            d.been_deleted = True
            d.save()
            auto_del_count += 1
            print("Auto delete Invalid doamin records {} in {}".format(m.domain, d.domain))

    return {'status': True, 'records': len(domain_add_list),
            "msg": "更新域名成功，共更新{}条记录，自动删除无效记录{}条".format(len(domain_add_list), auto_del_count), }


# 多域名批量执行
def multiple_flush(dms):
    for d in dms:
        print("Info Start Add or Flush domain: {}".format(d.domain))
        domain_add_new_relate(d)


def manual_execute(all_domains):
    """手动执行检查时间，初始化写入数据库"""
    for i in all_domains:
        print('test manual_execute {}'.format(i))
        # 一级域名
        the_primary_domain = analysis_primary_domain(i)
        # 解析地址，默认直连地址
        i_remote_addr = get_remote_addr(i)[1]
        # 一级域名 model 对象
        i_primary_domain, created = PrimaryDomain.objects.get_or_create(primary=the_primary_domain)
        # DomainList 对象
        i_domain, created = DomainList.objects.get_or_create(domain=i, defaults={'primary_domain': i_primary_domain, })
        # server， 不必加入get_or_create的 defaults
        i_server, created = ServerInfo.objects.get_or_create(ip=i_remote_addr, )
        i_domain.server = i_server
        i_domain.primary_domain = i_primary_domain
        if i_domain.port != 80:
            i_port = i_domain.port
        else:
            i_port = 443
        # 获取证书信息
        info = ssl_certificate_info(i, port=i_port)
        if info['status'] == 1:
            i_domain.start_time = info['start_time']
            i_domain.expire_time = info['expire_time']
            i_domain.set_multi_list(info['multi_name'])
            i_domain.port = i_port
            # 过期天数计算
            effective_days = (i_domain.expire_time - datetime.datetime.today()).days
            if effective_days < 14:  # 即将过期，少于14天
                i_domain.encryption = 2
            else:
                i_domain.encryption = 1
        elif info['status'] == 3:  # 已过期
            i_domain.encryption = 3
            i_domain.port = i_port
        elif info['status'] == 4:  # 连接被重置或被墙等连接不同的情况
            i_domain.encryption = 4
            i_domain.port = i_port
        else:  # 检验HTTPS证书失败
            i_domain.port = 80
            i_domain.encryption = 0
        i_domain.save()
