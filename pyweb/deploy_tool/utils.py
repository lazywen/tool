# -*- coding: utf-8 -*-

import os
import sys
import sqlite
import ConfigParser


operation_code = {
    1: 'deploy ios qfpay',
    2: 'deploy android qfpay',
    }


ROOT = os.path.dirname(os.path.abspath(__file__))


def get_operation_code(app_type):
    if app_type == 'ios_qfpay':
        return 1
    elif app_type == 'android_qfpay':
        return 2


def makedb(func):
    def _(self, *args, **kwargs):
        self.db = sqlite.open()
        return func(self, *args, **kwargs)
    return _


def makeconf(func):
    def _(self, *args, **kwargs):
        conf_path = os.path.join(ROOT, 'deploy.conf')
        cf = ConfigParser.ConfigParser()
        cf.read(conf_path)
        self.cf = cf
        return func(self, *args, **kwargs)
    return _


def get_user(func):
    def _(self, *args, **kwargs):
        self.login_user = self.get_secure_cookie("deploy_user")
        return func(self, *args, **kwargs)
    return _


def login_req(func):
    def _(self, *args, **kwargs):
        if self.get_secure_cookie("deploy_user") == None:
            self.redirect('/login')
            return
        return func(self, *args, **kwargs)
    return _

def check_success(cur, msg):
    cur.sendline('echo $?')
    cur.prompt()

    res = cur.before.split()

    for s in res:
        try:
            ret = int(s)
        except:
            pass
    
    if ret != 0:
        print "failed on %s" % msg
        sys.exit(-1)
