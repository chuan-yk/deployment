# #!/usr/local/python3.6/bin/python3
# # -*- coding:utf-8 -*-
# import os
# import datetime
# import paramiko
#
#
#
# class RemoteReplaceWorker(object):
#     def __init__(self, hostname,port, sshuser, sshpasswd, dstdir, fromfile, projectname, backupdir, tmpdir='/tmp'):
#         self.transport = paramiko.Transport((hostname, port))
#         self.transport.connect(username=sshuser, password=sshpasswd )
#         self.sshserver = paramiko.SSHClient()
#         self.sshserver._transport = self.transport
#         self.sftpserver = paramiko.SFTPClient.from_transport(self.transport)
#
#
#     def runtest(self):
#         for i in self.sshserver.exec_command('df -hl')[1]:
#             print(i, end='')
#         self.sshserver.close()
#         self.sftpserver.close()
#
# if __name__ == "__main__":
#     hostname='192.168.159.150'
#     port=22
#     sshuser = 'dendi'
#     sshpasswd = '123456'
#     tr = RemoteReplaceWorker(hostname,port, sshuser, sshpasswd)
#     tr.runtest()