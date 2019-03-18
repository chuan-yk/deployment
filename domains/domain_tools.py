import socket
import dns.resolver
# import os, django
import requests
import ssl
import datetime
import time

from cmdb.models import ServerInfo
from domains.models import PrimaryDomain, DomainList
from deployment.settings import logdft


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
        attr['region'] = r.content.decode().strip().split('来自:')[1].strip()
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
    if analysis:    # 自动解析域名证书
        ip = ServerInfo.objects.get(pk=server_id).ip
        info = ssl_certificate_info(domain, ip, port)
        attr['encryption'] = info.get('status')
        attr['start_time'] = info.get('start_time')
        attr['expire_time'] = info.get('expire_time')
        if info['multi_name']:
            attr['multi_cr'] = 1
            attr['multi_list'] = info.get('multi_name')
    the_domain, created = DomainList.objects.get_or_create(domain=domain, server_id=server_id, port=port,
                                                           defaults={'platform': attr.get('platform'),
                                                                     'cdn': attr.get('cdn', 0),
                                                                     'encryption': attr.get('encryption', 0),
                                                                     'multi_cr': attr.get('multi_cr', 0),
                                                                     'multi_list': attr.get('multi_list'),
                                                                     'start_time': attr.get('start_time'),
                                                                     'expire_time': attr.get('expire_time'),
                                                                     'been_deleted': attr.get('been_deleted', False),
                                                                     'note': attr.get('note'), }
                                                           )
    return the_domain, created


def ssl_certificate_info(domain, ip, port=443):
    """
    传入域名和指定解析IP,返回证书信息
    约定格式: {
        ‘status’： 0-未使用|1-使用中|2-连接不通或被墙|3-已过期|4-即将过期"，
        ‘start_time’: '证书生效时间',
        'expire_time': '证书过期时间'',
        ‘multi_name’: '共用证书的域名list' }
    #  django.db.utils.IntegrityError: 主键冲突错误
    """
    logdft('ssl_certificate_info check on {} {}， IP： {}'.format(domain, port, ip))
    info = {'status': 0, 'start_time': '', 'expire_time': '', 'multi_name': [], }
    ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'
    try:
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=domain, )
        conn.settimeout(3.0)  # 超时时间3秒
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
        print('{} {} ConnectionResetError , Reset connect , pass '.format(domain, port))
        return info
    # socket.timeout: timed out, 连接不通等待时间过长
    except socket.timeout:
        info['status'] = 2
        print('{} {} socket.timeout: timed out , pass '.format(domain, port))
        return info
    finally:
        if conn:
            conn.close()


# 新增域名自动解析
def domain_add_new_relate(m):
    primary_domain = analysis_primary_domain(m.domain)
    i_primary_domain, created = PrimaryDomain.objects.get_or_create(primary=primary_domain)
    m.primary_domain = i_primary_domain
    # 关联解析地址
    i_remote_addr = get_remote_addr(m.domain)[1]
    i_server, created = ServerInfo.objects.get_or_create(ip=i_remote_addr, )
    print(i_server)
    m.server = i_server
    return m


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
