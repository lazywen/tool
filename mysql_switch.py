#!/home/qfpay/python/bin/python
# coding: utf-8
import os, sys
import MySQLdb
import getopt
import subprocess
import re
import time
#import pexpect

#mysql_master = '192.168.100.6'
mysql_master = '172.100.101.100'

class MySQLInfo:
    def __init__(self, **kwargs):
        self.host = '127.0.0.1'
        self.port = 3306
        self.db = ''
        self.user = 'root'
        self.passwd = ''
        self.charset = 'utf8'
        self.logfile = None
        self.logpost = None

        if kwargs:
            self.__dict__.update(kwargs)

master_info = MySQLInfo(host=mysql_master, user='slave', passwd='123456')

class MySQLConnection:
    def __init__(self, info):
        self.conninfo = info
        self.conn = None
        #self.open()

    def open(self):
        if self.conn:
            self.conn.close()
        print 'open mysql at %s:%d' % (self.conninfo.host, self.conninfo.port)
        self.conn = MySQLdb.connect(host=self.conninfo.host,
                    user=self.conninfo.user,passwd=self.conninfo.passwd,db=self.conninfo.db,
                    port=self.conninfo.port,charset=self.conninfo.charset)

    def execute(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        cur.close()

    def query(self, sql, isdict=True):
        cur = self.conn.cursor()
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()

        if res and isdict:
            ret = []
            xkeys = [ i[0] for i in cur.description]
            for item in res:
                ret.append(dict(zip(xkeys, item)))
        else:
            ret = res
        return ret

    def get_variable(self, name):
        ret = self.query("show variables like '%s'" % name)
        return ret[0]['Value']

    def get_status(self, name):
        ret = self.query("show status like '%s'" % name)
        return ret[0]['Value']

    def slave_status(self):
        ret = self.query("show slave status")
        if ret:
            return ret[0]
        return None

    def master_status(self):
        ret = self.query("show master status")
        if ret:
            return ret[0]
        return None



def get_process(*names):
    cmd = "ps -elf | grep -v grep"
    for n in names:
        cmd += ' | grep ' + n
    print cmd
    x = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    lines = x.stdout.readlines()
    #print 'process line:', len(lines)
    return len(lines)

def localaddr():
    cmd = 'ifconfig -a | grep "inet addr"'
    x = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    lines = x.stdout.readlines()

    addrs = ['localhost']
    for line in lines:
        x = re.search('addr:([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', line)
        if x:
            addrs.append(x.groups()[0])

    return addrs

def check_master(conn, myinfo):
    '''检查是否是主'''
    print '\33[32mcheck for master ...\33[0m'
    conn.open()
    value = conn.get_status('Slave_running')
    if value == 'OFF':
        print 'ok, Slave_running:OFF'
    else:
        print 'failed, Slave_running:ON'
        return -1

    value = conn.get_variable('read_only')
    if value == 'OFF':
        print 'ok, read_only:OFF'
    else:
        print 'failed, read_only:ON'
        return -1

    return 0

def check_slave(conn, myinfo):
    '''检查是否是从'''
    print '\33[32mcheck for slave ...\33[0m'
    conn.open()
    value = conn.get_status('Slave_running')
    if value != 'OFF':
        print 'ok, Slave_running:ON'
    else:
        print 'failed, Slave_running:OFF'
        return -1

    value = conn.get_variable('read_only')
    if value != 'OFF':
        print 'ok, read_only:ON'
    else:
        print 'failed, read_only:OFF'
        return -1

    return 0


def check_master_virtual_ip():
    print '\33[32mcheck virtual ip:%s\33[0m' % mysql_master
    x = subprocess.Popen('ping -c 3 %s' % mysql_master, shell=True, stdout=subprocess.PIPE)
    lines = x.stdout.readlines()
    line = lines[-2]
    r = int(re.search('([0-9]+) received', line).groups()[0])
    if r > 0:
        print 'virtual ip exist:', r
    return r

def kill_virtual_ip():
    print '\33[32mkill virtual ip:%s\33[0m' % mysql_master
    cmd = 'killall vrrpd'
    count = 3
    while count > 0:
        print cmd
        os.system(cmd)
        time.sleep(1)
        if get_process('vrrpd') == 0:
            return 0
        cmd = 'killall -9 vrrpd'
        count -= 1
    return -1

def start_virtual_ip():
    print '\33[32mtry start virtual ip:%s\33[0m' % mysql_master
    #cmd = '/usr/local/bin/vrrpd -n -i bond0 -v 15 -p 100 %s' % mysql_master
    cmd = '/usr/local/bin/vrrpd -n -i eth0 -v 15 -p 100 %s' % mysql_master
    count = 3
    while count > 0:
        print cmd
        os.system(cmd)
        time.sleep(10)
        if get_process('vrrpd') > 0:
            return 0
        count -= 1

    return -1

def restart_mysql(name, info):
    print '\33[32mrestart mysql ...\33[0m'
    mycnf = 'my.cnf.%s' % name
    cmd = "mv /home/qfpay/mysql/etc/my.cnf /home/qfpay/mysql/etc/my.cnf.%d%02d%02d.%02d%02d%02d" % time.localtime()[:6]
    print cmd
    if os.system(cmd) != 0:
        return -1

    cmd = "cp /home/qfpay/mysql/etc/%s /home/qfpay/mysql/etc/my.cnf" % mycnf
    print cmd
    if os.system(cmd) != 0:
        return -1

    cmd = "/home/qfpay/mysql/bin/mysqladmin shutdown -u%s -p%s" % (info.user, info.passwd)
    if not info.passwd:
        cmd = "/home/qfpay/mysql/bin/mysqladmin shutdown -u%s" % (info.user)

    if get_process("mysqld") > 0:
        print 'shutdown mysql ...'
        if os.system(cmd) != 0:
            print 'shutdown error!'
            return -1

    cmd = '/home/qfpay/mysql/bin/mysqld_safe --user=qfpay &'
    print 'start mysql with %s' % mycnf
    if os.system(cmd) != 0:
        print 'start mysql error!'
        return -1

    time.sleep(5)
    x = raw_input('请检查mysql是否已经正常启动，已启动按回车继续，否则Ctrl-C退出')

    return 0

def to_master(conn, info):
    '''变为主'''
    print '\33[32mchange to master ...\33[0m'
    raw_input('请确认主从数据已同步完成，relay log已完全执行，且主不能写入数据。继续按回车键，Ctrl-c退出\33[0m')

    if kill_virtual_ip() != 0:
        print 'kill vrrpd error'
        return -1
    if check_master_virtual_ip() > 0:
        print '必须先停止虚拟ip:%s' % mysql_master
        return -1

    if restart_mysql('master', info) != 0:
        print 'restart mysql error!'
        return -1

    conn.open()

    cmd = [
           "stop slave",
           #"reset slave",
           "grant replication slave,reload on *.* to slave@'172.100.101.16' identified by '123456'",
           #"grant replication slave,reload,super on *.* to slave@'192.168.100.4' identified by 'MhxzKhl#@!qfpay'",
           "grant replication slave,reload on *.* to slave@'172.100.101.6' identified by '123456'",
           #"grant replication slave,reload,super on *.* to slave@'192.168.100.5' identified by 'MhxzKhl#@!qfpay'",
           "flush privileges",
           ]
    for c in cmd:
        print c
        conn.execute(c)

    if start_virtual_ip() != 0:
        print 'vrrpd start error!'
        return -1
    if check_master_virtual_ip() == 0:
        print '虚拟ip无法访问:%s' % mysql_master
        return -1

    print 'master server-id:', conn.get_variable('server_id')

    return 0

def to_slave(conn, info):
    '''变为从'''
    print '\33[32mchange to slave ...\33[0m'
    raw_input('请确认主从数据已同步完成，relay log已完全执行，且主不能写入数据。继续按回车键，Ctrl-c退出\33[0m')

    if kill_virtual_ip() != 0:
        print 'kill vrrpd error'
        return -1

    if restart_mysql('slave', info) != 0:
        print 'restart mysql error!'
        return -1

    conn.open()

    cmd = ["stop slave",
           "reset slave",
           "change master to master_host='%s',master_port=%d,master_user='%s',master_password='%s'" % \
                (master_info.host, master_info.port, master_info.user, master_info.passwd),
           "flush privileges",
           "start slave"
           ]

    if info.logfile:
        cmd[2] = cmd[2] + ",master_log_file='%s',master_log_pos=%d" % (info.logfile, info.logpos)

    for c in cmd:
        print c
        conn.execute(c)

    print 'slave server-id:', conn.get_variable('server_id')

    return 0

def master_to_slave(conn, info):
    '''由主变从'''
    print '\33[32mfrom master to slave ...\33[0m'
    ret = check_master(conn, info)
    if ret != 0:
        return -1
    to_slave(conn, info)


def slave_to_master(conn, info):
    '''由从变主'''
    print '\33[32mfrom slave to master ...\33[0m'
    ret = check_slave(conn, info)
    if ret != 0:
        return -1
    to_master(conn, info)


def help():
    print 'usage: mysql_switch.py [options]'
    print 'options:'
    print '\t-a to_master/to_slave/check_master/check_slave'
    print '\t-h mysql host'
    print '\t-u mysql user'
    print '\t-p mysql password'
    print '\t-f mysql master log file'
    print '\t-l mysql master log position'
    sys.exit(0)

def main():
    # host(h), user(u), passwd(p), action(a), logfile(f), logpos(l)
    args = sys.argv[1:]
    optlist, args = getopt.getopt(args, 'h:u:p:a:f:l:')
    opts = dict(optlist)

    if len(opts) == 0:
        help()

    action  = opts.get('-a')
    host    = opts.get('-h', '127.0.0.1')
    user    = opts.get('-u', 'root')
    passwd  = opts.get('-p', '')
    logfile = opts.get('-f')
    logpos  = opts.get('-l')

    if logfile or logpos:
        if not (logfile and logpos):
            print 'log file 和 log position 必须同时设置'
            return -1

    if action not in ['to_master','to_slave', 'check_master', 'check_slave']:
        print '-a error'
        return

    addrs = localaddr()
    print 'loadaddr:', addrs

    if action.startswith('to_') and host not in addrs:
        print 'host must in local addr'
        return

    info = MySQLInfo(host=host,user=user,passwd=passwd)
    if logfile:
        info.logfile = logfile
        info.logpos  = int(logpos)
    conn = MySQLConnection(info)

    if globals()[action](conn, info) != 0:
        print '\33[31merror!\33[0m'

    row = conn.slave_status()
    if row:
        print '-------------- slave status --------------'
        print 'Slave_IO_State:\t\t', row['Slave_IO_State']
        print 'Slave_IO_Running:\t', row['Slave_IO_Running']
        print 'Slave_SQL_Running:\t', row['Slave_SQL_Running']
        print 'Master_Host:\t\t', row['Master_Host']
        print 'Master_User:\t\t', row['Master_User']
        print 'Master_Port:\t\t', row['Master_Port']
        print 'Master_Server_Id:\t', row['Master_Server_Id']
        print 'Master_Log_File:\t', row['Master_Log_File']
        print 'Read_Master_Log_Pos:\t', row['Read_Master_Log_Pos']
        print 'Seconds_Behind_Master:\t', row['Seconds_Behind_Master']

    row = conn.master_status()
    if row:
        print '-------------- master status --------------'
        for k,v in row.iteritems():
            print k,'\t', v

if __name__ == '__main__':
    main()


