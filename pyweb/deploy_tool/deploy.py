#!/home/qfpay/python/bin/python
# -*- coding: utf-8 -*-
# Thu Oct 18 10:45:28 CST 2012


import os
import sys
import time
import tornado
import tornado.web
import mako
import traceback
import pexpect
import sqlite
import ConfigParser

from pssh import pxssh
from utils import makedb, makeconf, login_req, get_operation_code, check_success
from mako.template import Template
from mako.lookup import TemplateLookup
mako.runtime.UNDEFINED = ''

from mako.exceptions import TemplateLookupException


ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT_TEMPLATES = os.path.join(ROOT, 'templates')
ROOT_STATICS = os.path.join(ROOT, 'statics')
ROOT_APP = os.path.join(ROOT, 'apps')


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("deploy_user")


    lookup = TemplateLookup([ROOT_TEMPLATES])


    def render(self, template_name, **kwargs):
        """ Redefine the render """

        t = self.lookup.get_template(template_name)

        args = dict(
            handler=self,
            request=self.request,
            current_user=self.current_user,
            locale=self.locale,
            _=self.locale.translate,
            static_url=self.static_url,
            xsrf_form_html=self.xsrf_form_html,
            reverse_url=self.application.reverse_url,
        )

        args.update(kwargs)

        html = t.render(**args)
        self.finish(html)


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('main.html')


class AllRequestHandler(BaseHandler):
    def get(self, act):
        try:
            func = getattr(self, act)
            return func()
        except:
            traceback.print_exc()


    def post(self, act):
        return self.get(act)


    def login(self):
        self.render('login.html')


    def logout(self):
        self.clear_cookie('deploy_user')
        self.render('login.html', msg = "you have logout")


    @makedb
    def verify(self):
        try:
            user = self.get_argument('user')
            passwd = self.get_argument('passwd')
        except:
            self.redirect('/login')
            return

#        cur = sqlite.open()
        cur = self.db
        try:
            ret = cur.execute("select password from user where user='%s'" % user)
            psw = ret[0][0]
        except:
#            traceback.print_exc()
            self.render('login.html', msg="user error")
            return

        if passwd == psw:
            self.set_secure_cookie(name = "deploy_user", value = user, expires_days = 0.1)
            self.redirect('/')
        else:
            self.render('login.html', msg="password error")


    @login_req
    def android_qfpay(self):
        self.render('upload_app.html', 
            title="Upload android app:", 
            app_type="android_qfpay")


    @login_req
    def ios_qfpay(self):
        self.render('upload_app.html', 
            title="Upload ios app:", 
            app_type="ios_qfpay")
            

    @login_req
    def upload_file(self):
        msg_list = []
        try:
            app_type = self.get_argument('app_type')
        except:
            self.redirect('/')
            return
        try:
            app_file = self.request.files['app_file'][0]
            app_md5 = self.get_argument('app_md5')
            app_ver= self.get_argument('app_ver')
            passwd = self.get_argument('passwd')
        except:
            self.render('upload_app.html', 
                title="Upload %s app:" % app_type, 
                msg="please check", 
                app_type=app_type)
            return

        if len(app_md5) != 32:
            self.render('upload_app.html', 
                title="Upload %s app:" % app_type, 
                msg="md5 error", 
                app_type=app_type)
            return

        conf_path = os.path.join(ROOT, 'deploy.conf')
        cf = ConfigParser.ConfigParser()
        cf.read(conf_path)

        cp_path = cf.get(app_type, 'copy_path')
        de_path = cf.get(app_type, 'deploy_path')
        if app_type == 'android_qfpay':
            if str(app_file.get('filename')).find(r'.apk') < 0:
                self.render('upload_app.html', 
                    title="Upload %s app:" % app_type, 
                    msg="you should upload an apk file", 
                    app_type=app_type)
                return

            copy_path = os.path.join(cp_path, "Qianfang_v%s.apk" % app_ver)
            deploy_path = os.path.join(de_path, "Qianfang_v%s.apk" % app_ver)
            app_path = os.path.join(ROOT_APP, "Qianfang_v%s.apk" % app_ver)
            download_link = ["http://app.qfpay.com/app/Qianfang_v%s.apk" % app_ver, ]

        elif app_type == 'ios_qfpay':
            if str(app_file.get('filename')).find(r'.ipa') < 0:
                self.render('upload_app.html', 
                    title="Upload %s app:" % app_type, 
                    msg="you should upload an ipa file", 
                    app_type=app_type)
                return

            copy_path = os.path.join(cp_path, app_file.get('filename'))
            deploy_path = os.path.join(de_path, "QFPoS_v%s.ipa" % app_ver)
            app_path = os.path.join(ROOT_APP, "QFPoS_v%s.ipa" % app_ver)
            download_link = [
                "http://app.qfpay.com/app/ios/QFPoS_v%s.plist" % app_ver,
                "http://app.qfpay.com/app/ios/QFPoS_v%s.ipa" % app_ver,
            ]

        f = open(app_path, 'w')
        f.write(app_file.get('body'))
        f.close()
        msg_list.append('app upload success ...')


        user = cf.get('login', 'user')
        host = cf.get('login', 'host')


        dep = ExpectSsh(app_path, copy_path, deploy_path, user, passwd, host, app_md5, app_ver, app_type)
        cp = dep.copy_to_path()
        if cp:
            msg_list.append('copy to server success ...')
            d = dep.deploy_file(
                self.get_secure_cookie("deploy_user"),
                get_operation_code(app_type)
            )
            if d:
                msg_list.append('md5 check success ...')
                msg_list.append('deploy success !')
                self.render('result.html', msg_list=msg_list, go_mis=1, links=download_link)
            else:
                msg_list.append('md5 check failed, please rollback it ...')
                self.render('result.html', msg_list=msg_list)
        else:
            msg_list.append('copy to server failed, wrong password? or try to contant administrator.')
            self.render('result.html', msg_list=msg_list)


    @login_req
    def result(self):
        self.render('result.html', msg="test")


    @login_req
    @makedb
    def rollback_list(self):
        deploy_list = self.db.query("select * from deploy_list order by id desc")
        self.render('rollback_list.html', deploy_list=deploy_list)


    @login_req
    @makedb
    def rollback(self):
        try:
            roll_id = self.get_argument('roll_id')
            roll_data = self.db.query("select * from deploy_list where id=%d" % int(roll_id))[0]
            self.render(
                'passwd_form.html',
                roll_id = roll_id,
                user = 'qfpay',
                post_add = '/rollback_handle',
                roll_data = roll_data,
            )
        except:
            self.redirect('/rollback_list')


    @login_req
    def rollback_handle(self):
        try:
            roll_id = self.get_argument('roll_id')
            passwd = self.get_argument('password')
        except:
            self.redirect('/rollback_list')

        roll = RollBack(roll_id, passwd)
        ret = roll.rollback_it()

        if ret > 0:
            print 'failed'
            self.render('result.html', msg_list=['rollback failed',])
        else:
            print 'success'
            self.render('result.html', msg_list=['rollback success',])


    @login_req
    @makeconf
    def conf_login(self):
        cf = self.cf
        ret = {}
        ret[u'服务器'] = cf.get('login', 'host')
        ret[u'用户'] = cf.get('login', 'user')
        self.render('settings.html', settings=ret, title='login')


    @login_req
    @makeconf
    def conf_path(self):
        cf = self.cf
        ret = {}
        ret[u'index.html'] = cf.get('html_path', 'index_path')
        ret[u'android临时目录'] = cf.get('android_qfpay', 'copy_path')
        ret[u'android部署目录'] = cf.get('android_qfpay', 'deploy_path')
        ret[u'ios临时目录'] = cf.get('ios_qfpay', 'copy_path')
        ret[u'ios部署目录'] = cf.get('ios_qfpay', 'deploy_path')
        self.render('settings.html', settings=ret, title='path')


class RollBack:
    
    def __init__(self, roll_id, passwd):
        self.roll_id = roll_id
        self.passwd = passwd
        self.user = ''
        self.host = ''

        self.update_data()


    @makedb
    @makeconf
    def rollback_it(self):
        roll_data = self.db.query("select * from deploy_list where id=%d" % int(self.roll_id))[0]

        if not roll_data:
            return -1

        deployed_list = roll_data['deploy_path'].split()
        backup_list = roll_data['backup_path'].split()
        self.cmd_cur = self.try_login()

        ret_list = map(self.copy_back, backup_list, deployed_list)
        print ret_list

        index_path = self.cf.get('html_path', 'index_path')
        self.cmd_cur.sendline("cp %s %s_simple" % (index_path, index_path))
        self.cmd_cur.prompt()
        check_success(self.cmd_cur, 'rollback file')

        self.db.update("update deploy_list set status=0 where id=%d" % int(self.roll_id))
        return sum(ret_list)



    def copy_back(self, backup, deploy):
        if backup == '0' or backup ==0:
            return 0
        else:
            cur = self.cmd_cur
            cur.sendline("cp %s %s" % (backup, deploy))
            cur.prompt()

            cur.sendline("echo $?")
            cur.prompt()

            res = cur.before.split()

            for s in res:
                try:
                    ret = int(s)
                except:
                    pass
            
            return ret


    def update_data(self):
        conf_path = os.path.join(ROOT, 'deploy.conf')
        cf = ConfigParser.ConfigParser()
        cf.read(conf_path)

        self.user = cf.get('login', 'user')
        self.host = cf.get('login', 'host')


    def try_login(self):
        i = 0
        while(i < 3):
            try:
                s = pxssh()
                s.login(self.host, self.user, self.passwd)
                return s
            except:
                i += 1
        print "can not connecting to server %s" % self.host
        sys.exit(2)

            

class ExpectSsh:
    
    def __init__(self, appfile, copy_path, deploy_path, user, passwd, host, ora_md5, app_ver, app_type):
        self.user = user
        self.passwd = passwd
        self.host = host
        self.appfile = appfile
        self.copy_path = copy_path
        self.deploy_path = deploy_path
        self.ora_md5 = ora_md5
        self.app_type = app_type
        self.app_version = app_ver


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
        except:
            traceback.print_exc()
            return 0
        return 1


    def get_backup_path(self, cur, deploy_path):
        i = 0

        while(i < 1000):
            if i == 0:
                backup_path = "%s_%s" % (deploy_path, time.strftime('%Y%m%d'))
            else:
                backup_path = "%s_%s_%s" % (deploy_path, time.strftime('%Y%m%d'), i)

            cur.sendline("test -f %s" % backup_path)
            cur.prompt()
            cur.sendline("echo $?")
            cur.prompt()

            res = cur.before.split()

            for s in res:
                try:
                    ret = int(s)
                    if_exit = ret
                except:
                    pass
           
            if if_exit == 1:
               return backup_path
            else:
                i += 1

        return backup_path


    def backup_old_file(self, cur, deploy_path):
        cur.sendline("test -f %s" % deploy_path)
        cur.prompt()
        cur.sendline("echo $?")
        cur.prompt()

        res = cur.before.split()

        for s in res:
            try:
                ret = int(s)
                if_exit = ret
            except:
                pass

        if if_exit == 0:
            backup_path = self.get_backup_path(cur, deploy_path)
            cur.sendline("cp %s %s" % (deploy_path, backup_path))
            cur.prompt()
            check_success(cur, 'backup %s' % deploy_path)
            return backup_path
        else:
            return 0



    @makedb
    def deploy_file(self, login_user, operation):
        backup_list = []
        deploy_list = []

        cur = self.try_login()
        app_backup = self.backup_old_file(cur, self.deploy_path)
        backup_list.append(str(app_backup))
        deploy_list.append(self.deploy_path)

        cur.sendline("cp %s %s" % (self.copy_path, self.deploy_path))
        cur.prompt()
        check_success(cur, 'deploy %s' % self.deploy_path)

        cur.sendline("md5sum %s" % self.deploy_path)
        cur.prompt()
        ret = cur.before

        md5 = self.get_md5(ret.split())

        conf_path = os.path.join(ROOT, 'deploy.conf')
        cf = ConfigParser.ConfigParser()
        cf.read(conf_path)

        index_path = cf.get('html_path', 'index_path')
        index_backup = self.backup_old_file(cur, index_path)
        backup_list.append(str(index_backup))
        deploy_list.append(index_path)

        if self.app_type == 'android_qfpay':
            cur.sendline('''python -c "import re; body=re.sub('Qianfang[a-zA-Z0-9\._]*\.apk', 'Qianfang_v%s.apk', open('%s_simple').read());f=open('%s','w');f.write(body.__str__());f.close()"''' % (self.app_version, index_path, index_path))
            cur.prompt()
            check_success(cur, 'modify index %s' % index_path)
        elif self.app_type == 'ios_qfpay':
            plist_path = os.path.join(cf.get('ios_qfpay', 'deploy_path'), "QFPoS_v%s.plist" % self.app_version)
            plist_backup = self.backup_old_file(cur, plist_path)
            plist_simple = os.path.join(cf.get('ios_qfpay', 'deploy_path'), "QFPoS.plist_simple")

            backup_list.append(str(plist_backup))
            deploy_list.append(plist_path)

            cur.sendline('''python -c "import re; body=re.sub('QFPoS[a-zA-Z0-9\._]*\.ipa', 'QFPoS_v%s.ipa', open('%s').read());f=open('%s','w');f.write(body.__str__());f.close()"''' % (self.app_version, plist_simple, plist_path))
            cur.prompt()
            check_success(cur, 'modify plist %s' % index_path)

            cur.sendline('''python -c "import re; body=re.sub('QFPoS[a-zA-Z0-9\._]*\.plist', 'QFPoS_v%s.plist', open('%s_simple').read());f=open('%s','w');f.write(body.__str__());f.close()"''' % (self.app_version, index_path, index_path))
            cur.prompt()
            check_success(cur, 'modify index %s' % index_path)

        cur.sendline("cp %s %s_simple" % (index_path, index_path))
        cur.prompt()
        check_success(cur, 'copy to simple')

        cur_sql = self.db
        cur_sql.insert(
            "insert into deploy_list(user,operation,app_version,backup_path,deploy_path,stime,status) values(?,?,?,?,?,?,?)", 
            [(login_user, operation, self.app_version, ' '.join(backup_list), ' '.join(deploy_list), time.strftime("%Y-%m-%d %H:%M:%S"), 1),]
        )

        if md5 == self.ora_md5:
            print 'md5 ok'
            return 1
        else:
            print 'md5 failed'
            return 0


    def get_md5(self, data):
        for d in data:
            if len(d) == 32:
                return d
        return 0


    def verify_md5(self, md5):
        if md5 == self.ora_md5:
            print 'md5 ok'
            print 'deploy seccuss !'
        else:
            print 'md5 failed ! exit'
            sys.exit(-1)


    def try_login(self):
        i = 0
        while(i < 3):
            try:
                s = pxssh()
                s.login(self.host, self.user, self.passwd)
                return s
            except:
                i += 1
        print "can not connecting to server %s" % self.host
        sys.exit(2)


settings = {
    "static_path": ROOT_STATICS,
    "cookie_secret": "34oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    "login_url": "/login",
    "xsrf_cookies": True,
    }


application = tornado.web.Application([
    (r'/', MainHandler),
    (r'/(.+)', AllRequestHandler),
], **settings)


if __name__ == '__main__':
    application.listen(8980)
    tornado.ioloop.IOLoop.instance().start()
