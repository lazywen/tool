# coding: utf-8

import os
import sys
import time
import pexpect
import getpass
import traceback

from pssh import pxssh


#本地apk的路径
appfile = "/tmp/ee.apk"
#复制到服务器保存的临时位置
copy_path = "/tmp/aaaaaa.apk"
#部署的准确位置
deploy_path = "/home/lishiwen/mytest/ds.apk"
#登录用户、密码、服务器ip
user = "lishiwen"
passwd = getpass.getpass("input passwd for %s:" % user)
host = "172.100.101.14"
#本地md5sum的值
ora_md5 = "44f981754d069bf6bd656601a43a8db5"


class ExpectSsh:
    
    def __init__(self, appfile, copy_path, deploy_path, user, passwd, host, ora_md5):
        self.user = user
        self.passwd = passwd
        self.host = host
        self.appfile = appfile
        self.copy_path = copy_path
        self.deploy_path = deploy_path
        self.ora_md5 = ora_md5


    def copy_to_path(self):
        cmd = "scp %s %s@%s:%s" % (self.appfile, self.user, self.host, self.copy_path)
        child = pexpect.spawn(cmd)

        try:
            exp = child.expect(['password:','continue connecting (yes/no)?'])
            if exp == 0:
                child.sendline(self.passwd)
            elif exp == 1:
                child.sendline('yes')
                child.expect('password:')
                child.sendline(passwd)

            child.expect('100%')
            print "copy to server seccuss"
        except:
            print "passwd error"
            traceback.print_exc()
            sys.exit(-1)
        return 


    def deploy_file(self):
        cur = self.try_login()

        cur.sendline("md5sum %s" % self.copy_path)
        cur.prompt()
        ret = cur.before
        md5 = self.get_md5(ret.split())
        self.verify_md5(md5)

        backup_path = "%s_%s" % (self.deploy_path, time.strftime('%Y%m%d'))
        cur.sendline("cp %s %s" % (self.deploy_path, backup_path))
        cur.prompt()
        print "backup file to %s" % backup_path

        cur.sendline("cp %s %s" % (self.copy_path, self.deploy_path))
        cur.prompt()
        print "deploying file %s" % self.deploy_path

        cur.sendline("md5sum %s" % self.deploy_path)
        cur.prompt()
        ret = cur.before

        md5 = self.get_md5(ret.split())
        self.verify_md5(md5)


    def verify_md5(self, md5):
        if md5 == self.ora_md5:
            print 'md5 ok'
            print 'deploy seccuss !'
        else:
            print 'md5 failed ! exit'
            sys.exit(-1)


    def get_md5(self, data):
        for d in data:
            if len(d) == 32:
                return d
        return 0


    def try_login(self):
        i = 0
        while(i < 3):
            try:
                s = pxssh()
                s.login(self.host, self.user, self.passwd)
                return s
            except:
                traceback.print_exc()
                i += 1
        print "can not connecting to server %s" % self.host
        sys.exit(2)


def main():
    s = ExpectSsh(appfile, copy_path, deploy_path, user, passwd, host, ora_md5)
    s.copy_to_path()
    s.deploy_file()


if __name__ == '__main__':
    main()
