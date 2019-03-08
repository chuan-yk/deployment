import socket
import dns.resolver
# import os, django
import ssl
import datetime
import time

from cmdb.models import ServerInfo
from domains.models import PrimaryDomain, DomainList


def get_dns_resolver(domain):
    res = dns.resolver.Resolver()
    try:
        query_result = res.query(domain)
        ip_address = ''
        for i in query_result.response.answer:
            for j in i:
                ip_address = j
        return [domain, ip_address]
    except dns.resolver.Timeout:
        print('{0} check_domain_dns_records by query DNS server , query DNS time out'.format(domain))
        return [domain, 'unknown']
    except Exception as err:
        print(str('{} check_domain_dns_records by query DNS server ,'.format(domain)) + str(err))
        return [domain, 'unknown']


def get_remote_addr(domain):
    print('get_remote_addr check on {}'.format(domain))
    try:
        result = socket.gethostbyname_ex(domain)
        return [domain, result[2][0], result[2], result[1], ]
    except IndexError as err:
        print('get_remote_addr IndexError', err)
        return [domain, '0.0.0.0', [], [], [], ]
    except socket.gaierror as err:
        print('get_remote_addr err:', err)
        return [domain, '0.0.0.0', [], [], [], ]
    except ConnectionResetError as err:
        print('get_remote_addr connect err:', err)
        return [domain, '0.0.0.0', [], [], [], ]


def ssl_certificate_info(domain, port=443):
    """传入域名， 返回证书信息，约定格式 {‘status’： 1成功|0失败|3已过期|4连接不通或被墙， ‘start_time’: '', 'expire_time': '', ‘multi_name’: '' }"""
    print('ssl_certificate_info check on {} {}'.format(domain, port))
    info = {'status': 0, 'start_time': '', 'expire_time': '', 'multi_name': [], }
    ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'
    try:
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=domain, )
        # 3 second timeout
        conn.settimeout(3.0)
        conn.connect((domain, port))
        ssl_info = conn.getpeercert()
        info['status'] = 1
        info['expire_time'] = datetime.datetime.strptime(ssl_info['notAfter'], ssl_date_fmt)
        info['start_time'] = datetime.datetime.strptime(ssl_info['notBefore'], ssl_date_fmt)
        for i in ssl_info['subjectAltName']:
            info['multi_name'].append(i[1])
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
        info['status'] = 4
        print('{} {} ConnectionResetError , Reset connect , pass '.format(domain, port))
        return info
    # socket.timeout: timed out, 连接不通等待时间过长
    except socket.timeout:
        info['status'] = 4
        print('{} {} socket.timeout: timed out , pass '.format(domain, port))
        return info
    finally:
        if conn:
            conn.close()


def analysis_primary_domain(domain_name):
    fragmentation_list = domain_name.split('.')
    the_primary_domain = '.'.join(fragmentation_list[-2:])
    return the_primary_domain


def domain_add_new_relate(m):
    # 关联主域名
    primary_domain = analysis_primary_domain(m.domain)
    i_primary_domain, created = PrimaryDomain.objects.get_or_create(primary=primary_domain)
    print(i_primary_domain)
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
        elif info['status'] == 3:   # 已过期
            i_domain.encryption = 3
            i_domain.port = i_port
        elif info['status'] == 4:   # 连接被重置或被墙等连接不同的情况
            i_domain.encryption = 4
            i_domain.port = i_port
        else:      # 检验HTTPS证书失败
            i_domain.port = 80
            i_domain.encryption = 0
        i_domain.save()


def main():
    dm_list = []
    with open('/tmp/domain_list.txt', 'r') as f:
        f_lines = f.readlines()
    for i in f_lines:
        the_domain = i.strip()
        resolve = get_remote_addr(the_domain)
        time.sleep(0.5)
        try:
            info = ssl_certificate_info(the_domain)
            print("{:^20} 解析地址:{:<20} 过期时间: {:<20}  同证书域名: {}".format(the_domain, resolve[1], str(info['expire_time']),
                                                                      info['multi_name']))
        except Exception as e:
            print(the_domain, e)
