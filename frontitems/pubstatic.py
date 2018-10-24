#!/usr/local/python3.6/bin/python3
# -*- coding:utf-8 -*-
import subprocess
import os
import sys
import datetime
import getopt

class ReplaceWorker(object):
    def __init__(self, dstdir, fromfile, projectname, backupdir, ):
        self.dstdir = dstdir
        self.fromfile = fromfile
        self.projectname = projectname
        self.operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        #self.backupdir = os.path.join(backupdir, '{0}_V_{1}'.format(self.projectname, self.operatingtime))
        self.backupdir = backupdir
        self.errormessage = {}
        self.errormessage['special'] = []
        self.backupsuccess= None
        self.coversuccess = None
        self.backupdirlist=[]
        self.newfilelist = []
        self.newdirlist = []
        self.coverfailurelist = []
        self.unzipcreatealldir = set()
        self.unzipcreatedir = set()
        self.unzipcreatefile = []
        self.unzipdir = subprocess.getstatusoutput('mktemp -t -d unzipstatic.XXXX')[1]
        os.chdir(self.unzipdir)
        self.unzipfile()                        # self.unzipsuccess ,
        if self.unzipsuccess:
            self.exploredecompressed()          # change self.unzipcreatedir,  self.unzipcreatefile
            self.checkfile()                    # self.newfilelist ,self.newdirlist

    def unzipfile(self):
        try:
            os.chdir(self.unzipdir)
            unzipresult = subprocess.getstatusoutput('unzip -q {0}'.format(self.fromfile))
            if unzipresult[0] != 0:
                self.errormessage['unziperror'] = unzipresult[1]
                self.unzipsuccess = False
                return None
            else:
                self.unzipsuccess = True
        except Exception as e:
            self.errormessage['unziperror'] = str(e)
            print('some error')
            exit(2)

    def exploredecompressed(self):
        # set: unzipcreatedir -add ; list:unzipcreatefile
        if not self.unzipsuccess:
            return None
        for root, dirs, files in os.walk(os.path.join(self.unzipdir, '_dist'), topdown=False, followlinks=False):
            for dirname in dirs:
                none_dict_dir = os.path.join(root,dirname).split('_dist/')[1:]
                try:
                    self.unzipcreatealldir.add(none_dict_dir[0].strip('/'))
                    self.unzipcreatedir.add(os.path.join(*none_dict_dir[0].split('/')[0:2]))
                except:
                    pass
            for file in files:
                try:
                    self.unzipcreatefile.append(os.path.join(root, file).split('_dist/')[1:][0])
                except:
                    pass
        try:
            self.unzipcreatedir.remove('static')
        except:
            pass

    def checkfile(self):
        for file in self.unzipcreatefile:
            if not os.path.isfile(os.path.join(self.dstdir, file)):
                self.newfilelist.append(file)

        for dir in self.unzipcreatealldir:
            if not os.path.isdir(os.path.join(self.dstdir, dir)):
                self.newdirlist.append(dir)
        for dir in self.newdirlist:                                 # remove new create dir
            try:
                self.unzipcreatedir.remove(dir)
            except:
                pass

    def backupoldfile(self):
        if not self.unzipsuccess:                                   # exec condition = unzipsuccess
            return None
        try:
            for dir in self.unzipcreatedir:
                back_to_file = os.path.join('{0}_V_{1}'.format(self.projectname, self.operatingtime), dir )
                os.system('mkdir -p {}'.format(os.path.join(self.backupdir,back_to_file)))
                backupresult = subprocess.getstatusoutput('/bin/cp -r {0} {1}'.format(os.path.join(self.dstdir, dir), os.path.dirname(os.path.join(self.backupdir,back_to_file)) ) )
                if backupresult[0] == 0:
                    self.backupdirlist.append(back_to_file)
                    self.backupsuccess = True
                else:
                    self.errormessage['backuperror'] = backupresult[1]
                    self.backupsuccess = False
                    print('back up error --!')
        except Exception as e:
            self.errormessage['backuperror'] = str(e)
            self.backupsuccess = False
            #log

    def cover(self):
        if not self.backupsuccess:
            return None
        if os.curdir != self.unzipdir:
            os.chdir(self.unzipdir)
        try:
            coverfailure_flag = 0
            for file in self.unzipcreatefile:
                if file in self.newfilelist:
                    continue
                coverresult = subprocess.getstatusoutput("/bin/cp -r '{0}' '{1}'".format(os.path.join(os.curdir, '_dist', file), os.path.join(self.dstdir, file)))
                if coverresult[0]:
                    coverfailure_flag += 1
                    self.coverfailurelist.append(file)
                    self.errormessage['covererror'] = coverresult[1]
            else:
                if not coverfailure_flag:
                    self.coversuccess = True
            # else:
            #     self.coversuccess = True
            #     pass    #logger
        except Exception as e:
            self.errormessage['covererror'] = str(e)
            self.coversuccess = False

    def cover_ignore_newfile(self):
        if not self.backupsuccess:
            return None
        if os.curdir != self.unzipdir:
            os.chdir(self.unzipdir)
        coverfailure_flag = 0
        for newdir in self.newdirlist:
            os.makedirs(os.path.join(self.dstdir, newdir))
        for dir in list(self.unzipcreatealldir) :
            dir_cover_result = subprocess.getstatusoutput("/bin/cp -r '{0}' '{1}'".format(os.path.join(os.curdir, '_dist', dir), os.path.dirname(os.path.join(self.dstdir, dir))))
            if dir_cover_result[0]:
                coverfailure_flag += 1
                self.errormessage['dir_cecover_error'] = dir_cover_result[1]
                self.coversuccess = None
                print('cover {} failure !'.format(dir))
        else:
            if not coverfailure_flag:
                self.coversuccess = True

    def cleantemp(self):
        if self.coversuccess:
            os.system(' find /tmp/unzipstatic* -mtime +7 -exec rm -rf {} \; ')  # Safety way !

    def run(self):
        self.backupoldfile()
        self.cover()
        self.cleantemp()
        return {
            'unzip':self.unzipsuccess, 'backup':self.backupsuccess, 'cover':self.coversuccess,
            'backuplist':self.backupdirlist, 'newdir':self.newdirlist, 'newfile':self.newfilelist,
            'errormessage':self.errormessage, 'pub_dir':list(self.unzipcreatedir),
            }

    def ignore_newfile_run(self):
        self.backupoldfile()
        self.cover_ignore_newfile()
        self.cleantemp()
        return {
            'unzip': self.unzipsuccess, 'backup': self.backupsuccess, 'cover': self.coversuccess,
            'backuplist': self.backupdirlist, 'newdir': self.newdirlist, 'newfile': self.newfilelist,
            'errormessage': self.errormessage,'pub_dir':list(self.unzipcreatedir) + self.newdirlist,
        }

class  ReplaceWorker1(object):
    def __init__(self, dstdir, fromfile, projectname, backupdir, ):
        self.dstdir = dstdir
        self.fromfile = fromfile
        self.projectname = projectname
        self.operatingtime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        #self.backupdir = os.path.join(backupdir, '{0}_V_{1}'.format(self.projectname, self.operatingtime))
        self.backupdir = backupdir
        self.errormessage = {}
        self.errormessage['special'] = []
        self.backupsuccess= None
        self.coversuccess = None
        self.backupdirlist=[]
        self.newfilelist = []
        self.newdirlist = []
        self.coverfailurelist = []
        self.unzipcreatealldir = set()
        self.unzipcreatedir = set()
        self.unzipcreatefile = []


def docommand():
    #linux command execute
    configlist = {'platform':'mc', 'dstdir':'/var/www/html', 'backdir':'/backup/mc', 'keep_dir':'/data/release/mc', 'http_addr':'116.93.5.2:83/tk',
                  'sobet':'sobet.zip', 'lottery':'lottery.zip', 'lottery_m':'lottery_m.zip', 'sport':'sport.zip',
                  '1': 'sobet.zip', '2': 'lottery.zip', '3': 'lottery_m.zip', '4': 'sport.zip',
                  'valid_name':['sobet', 'lottery', 'lottery_m', 'sport'],
                  }
    # configlist = {'platform':'md', 'dstdir':'/var/www/html/xpt', 'backdir':'/backup/xpt', 'keep_dir':'/data/release/xpt', 'http_addr':'116.93.5.2:83',
    #               'sobet': 'md_sobet.zip', 'lottery': 'md_lottery.zip', 'lottery_m': 'md_lottery_m.zip', 'sport': 'md_sport.zip',
    #               '1': 'md_sobet.zip', '2': 'md_lottery.zip', '3': 'md_lottery_m.zip', '4': 'md_sport.zip',
    #               'valid_name':['sobet', 'lottery', 'mobile', 'sport']
    #               }
    ignore_new_do_cover_tag = False
    projt = ''
    argv = sys.argv[1:]
    opts = ''
    show_all_error = False
    def print_help():
        print("Usage: {0} -p [sobet 1|lottery 2|lottery_m 3|sport 4]".format(sys.argv[0]))
        print("Usage: {0} -p [sobet 1|lottery 2|lottery_m 3|sport 4] [--project=sobet 1|lottery 2...] --ignore_new -i (ignore_new)".format(sys.argv[0]))
        exit(0)
    def get_tk_file(projt):
        tmp_save_path = os.path.join(configlist['keep_dir'], datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        try:
            if subprocess.getstatusoutput('mkdir -p {}'.format(tmp_save_path))[0] != 0:
                raise Exception('Error: ','mkdir -p {}'.format(tmp_save_path))
            os.chdir(tmp_save_path)
            getfile_result = subprocess.getstatusoutput('wget {}/{}'.format(configlist['http_addr'], configlist['{}'.format(projt)]))
            if getfile_result[0] != 0:
                raise Exception(getfile_result[1])
            return os.path.join(tmp_save_path, configlist['{}'.format(projt)])

        except Exception as e:
            with open('readme.txt', 'w+') as f:
                f.write(str(e))
                print('\033[93m function get_tk_file ' + '{}'.format(e) + ' ! more info check {}\033[0m'.format(
                    tmp_save_path))
            sys.exit(1)


    try:
        opts, args = getopt.getopt(argv, "hp:i", ["help", "project=", "ignore_new", "debug"])
    except:
        print_help()
        exit(2)
    for opt, arg in opts:
        if opt in ['-h', '--help']:
            print_help()
        elif opt in ['-p', '--project']:
            try:
                if len(arg) == 1 and int(arg) < 5:
                    projt = configlist['valid_name'][int(arg)-1]
                elif arg in configlist['valid_name']:
                    projt = arg
                else:
                    raise Exception(arg, 'is invalid, It must match ', configlist['valid_name'])
            except TypeError:
                print_help()
            except Exception as e:
                print(e)
                print_help()
        elif opt in ['-i', '--ignore_new']:
            ignore_new_do_cover_tag = True
        elif opt in ['--debug']:
            show_all_error = True
    if not projt:print_help()
    fromfile = get_tk_file(projt)
    if projt == 'lottery_m':configlist['dstdir'] = os.path.join(configlist['dstdir'], 'mobile')
    tasker = ReplaceWorker(configlist['dstdir'], fromfile, projt, configlist['backdir'] )
    if ignore_new_do_cover_tag:
        this_result = tasker.ignore_newfile_run()
    else:
        this_result = tasker.run()
    if show_all_error:
        for key in this_result:
            print(key)
            print(this_result[key])
    if this_result['cover']:
        print('\033[95m'+ '文件已备份到:' + '\033[0m')
        for i in this_result['backuplist']: print('\033[96m' + '    {:<30}'.format(i) + '\033[0m')
        print('\033[95m'+ '更新文件夹:' + '\033[0m')
        for i in this_result['pub_dir']:print('\033[96m'+ '    {:<30}'.format(i) + '\033[0m')
        if len(this_result['newfile']) and not ignore_new_do_cover_tag:#newdir newfile
            print('-'*100)
            print('\033[93m'+ '如下新增文件(夹)默认未覆盖，如需覆盖请添加参数 "-i", "--ignore_new" ' + '\033[0m')
            for i in this_result['newdir']:print('\033[91m'+ '新文件夹    {}'.format(i) + '\033[0m')
            for i in this_result['newfile']:print('\033[91m'+ '新文件    {}'.format(i) + '\033[0m')
        print('\033[91m发布完成！\033[0m')
    else:
        if this_result['unzip'] and this_result['backup'] == None:
            print('请检查 configlist[dstdir]')
        if show_all_error:
            print(this_result)
        else:
            print(this_result['errormessage'])
        print('\033[93m发布失败！！！！！！请检查错误日志\033[0m')


if __name__ == '__main__':
    docommand()