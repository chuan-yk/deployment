import configparser,datetime
from django.shortcuts import render, redirect
from .remote_run import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from tempfile import NamedTemporaryFile



hostConf = 'D:\\Projects\\deployment\\autojar\\host.conf'
appConf = 'D:\\Projects\\deployment\\autojar\\apppath.conf'

def prepareConfig(section, appname, filenames=hostConf):
    configdata = configparser.ConfigParser()
    configdata.read(filenames)
    if appname == 'sobet':
        Result = configdata.get(section, appname)
    if appname == 'lottery':
        Result = configdata.get(section, appname)
    if appname == 'admin':
        Result = configdata.get(section, appname)

    return Result

@login_required
def upload_file(request):
    upload_path = "D:\\Projects\\deployment\\autojar\static\\upload"
    if request.method == "POST":
        ptid = request.POST.get('plafrom')         #获取平台
        appid = request.POST.get('appname')        #获取app项目
        File = request.FILES.get("myfile", None)   # 获取上传的文件,如果没有文件,则默认为None;
        action = request.POST.get('action')        #是否重启tomcat应用 0不重启,1重启
        if File is None:
            return redirect('autojar: jar_upload',messages.error(request,'没有选择文件!','alert-danger'))
        else:
            #with open(upload_path+File.name, 'wb+') as f:
            with NamedTemporaryFile('wb+',delete=False,prefix=File.name,dir=upload_path) as f:
                for chunk in File.chunks():         # 分块写入文件;
                    f.write(chunk)
                    f.close()
            ResultdicExe = RunCommd(ptid,appid,File.name,f.name,action)
            Resultdic = deldicNullkey(ResultdicExe)

            if 'Resultstderr' in ResultdicExe.keys():
                messages.error(request,'发布失败','alert-danger')
                return render(request, 'autojar/upload.html', Resultdic)
            messages.success(request, '发布成功！', 'alert-success')
            return render(request, 'autojar/upload.html', Resultdic)

                #return render(request, 'upload.html', Resultdict[0], Resultdict[1].success(request, '发布成功', 'alert-success'))
                #return redirect('/deoply/jar', messages.error(request, '发布失败!', 'alert-danger'))
    else:
        return render(request, 'autojar/upload.html')

def RunCommd(ptname,appname,Fname,fname,action=0):
    datenow = datetime.datetime.now().strftime('%Y%m%d-%H%M')
    t = SSHManager(prepareConfig(ptname, appname), 22)
    t.ssh_connect()
    url = 'http://127.0.0.1/'
    path = '/tmp/' + os.path.split(fname)[1]

    execResult = t.ssh_exec_cmd('''wget -T 3 -q {url}{tmpname1} -P /tmp/{tmpname};
               cp -r {apppath}webapps/{appname} /back/{appname}_{date};
               unzip -q /tmp/{tmpname}/{tmpname1} -d /tmp/{tmpname}/{name};
                cd {expath};
                jar -uvf {apppath}lib/{name}.jar {name}
                '''.format(url=url, tmpname1='jstl.zip', tmpname=os.path.split(fname)[1],
                name=os.path.splitext(Fname)[0], expath=path,appname=appname,date=datenow,
                apppath=prepareConfig(ptname, appname,appConf)))

    Resultdic = {'Title': '执行结果', 'Resultstdout': execResult[0][:-1].split('\n'),
                 'Resultstderr': execResult[1][0:-1].split('\n')}


    if execResult[2] != 0:
        return Resultdic
    if action == '1':
        print('restart')
        result = t.ssh_exec_cmd('''
        ps -ef|grep {apppath}conf|grep -v grep |grep -v tail|xargs kill -9;
        {apppath}bin/startup.sh
        '''.format(apppath=prepareConfig(ptname, appname,appConf)))
        #print(result)
    print(Resultdic)
    return  Resultdic


def deldicNullkey(dic):
    for key,value in list(dic.items()):  #字典在遍历时无法变更,建议采用list和tuple后再操作
        if len(dic[key]) <= 1:
            del dic[key]
    return dic

