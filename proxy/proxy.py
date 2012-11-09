#!/home/qfpay/python/bin/python
# -*- coding: utf-8 -*-
# Fri Nov  2 17:17:53 CST 2012


import os
import sys
import time
import pycurl
import pexpect
import logging
import StringIO
import traceback

_log = '/tmp/proxy.log'
_pid = '/tmp/proxy.pid'

_connect = {
    'user': 'username',
    'passwd': '654321',
    'host': '62.65.65.65',
    'local_port': '7070',
}

_status = {
    '00': 'proxy ok',
    '01': 'network ok, proxy err',
    '11': 'network err',
    '22': 'status change',
}


def loginit():
    logger  = logging.getLogger()
    if _log == 'stdout':
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(_log)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.setLevel(logging.NOTSET)
    return logger

log = loginit()


class WatchDog:
    def __init__(self):
        self.begin = 0
        self.end = 600
        self.watch_now = 10


    def get_watch(self, reset = False):
        if reset:
            self.reset()

        if self.watch_now >= self.end:
            return self.end
        else:
            self.watch_now += 15
            return self.watch_now


    def reset(self):
        self.watch_now = self.begin



class ConnRetry:
    def __init__(self):
        self.MAX_RETRY = 10
        self.retry = 0


    def set(self):
        self.retry += 1

        if self.retry >= self.MAX_RETRY:
            log.error('ssh connect fialed')
            sys.exit(-2)


    def reset(self):
        self.retry = 0



class SshClient:
    def __init__(self, kwargs):
        self.RUN = True
        self.status = '11'
        self.socket_error = 0
        self.watch_dog = WatchDog()
        self.rt = ConnRetry()

        if kwargs:
            self.__dict__.update(kwargs)


    def WATCH(self, reset):
        return self.watch_dog.get_watch(reset)


    def set_status(self, s):
        self.status = s


    def check_network(self, proxy=False):
        c = pycurl.Curl()
        c.setopt(pycurl.URL, 'http://m.baidu.com')
        c.setopt(pycurl.TIMEOUT, 5)
        b = StringIO.StringIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)

        if proxy:
            c.setopt(pycurl.PROXY, 'localhost')
            c.setopt(pycurl.PROXYPORT, int(self.local_port))
            c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)

        try:
            c.perform()
            ret = b.getvalue()
            if ret:
                return True
            else:
                return False
        except:
            log.warn(traceback.format_exc())
            return False


    def get_proc_sta(self, what):
        if what == 'py':
            process = __file__
        elif what == 'ssh':
            process = "ssh -qTfnN %s@%s" % (self.user, self.host)

        c = os.popen("ps -ef | grep '%s' | grep -v 'grep'" % process)
        ret = c.readlines()
        return ret


    def get_pid(self, what):
        ret = self.get_proc_sta(what)[0]
        return int(ret.split()[1])


    def set_pid(self):
        pid = self.get_pid('py')
        f = open(_pid, 'w')
        f.write(str(pid))
        f.close()


    def check_process(self, what):
        ret = self.get_proc_sta(what)

        if len(ret) >= 1:
            return True
        else:
            return False


    def start_process(self, restart=False):
        self.rt.set()
        if restart:
            self.stop_process()

        pid = os.fork()
        if pid == 0:
            child = pexpect.spawn(
                '''ssh -qTfnN %s@%s -D 127.0.0.1:%s''' % (self.user, self.host, self.local_port)
            )

            try:
                exp = child.expect(['password:','continue connecting (yes/no)?'])
                if exp == 0:
                    child.sendline(self.passwd)
                elif exp == 1:
                    child.sendline('yes')
                    child.expect('password:')
                    child.sendline(self.passwd)
                time.sleep(10)
            except:
                child.close()
                log.warn("can not connecting to server %s" % self.host)
            os._exit(0)
        return



    def stop_process(self):
        pid = self.get_pid('ssh')
        r = os.system("kill -9 %s" % pid)
        if r == 0:
            return
        else:
            sys.exit(-2)


    def main_process(self):
        while(self.RUN):
            self.set_pid()

            if self.check_network():
                time.sleep(2)

                if self.check_network(proxy = True):
                    s = self.WATCH(self.status != '00')
                    log.info('status:00 pid:%s next:%s' % (self.get_pid('ssh'),s))
                    self.set_status('00')
                    self.rt.reset()
                    self.socket_error = 0
                    time.sleep(s)
                    continue
                else:
                    if not self.check_process('ssh'):
                        self.start_process()
                    else:
                        if self.socket_error >= 4:
                            self.start_process(True)
                            self.socket_error = 0
                            self.set_status('22')
                        else:
                            self.socket_error += 1

                    s = self.WATCH(self.status != '01')
                    log.warn('status:01 socket_err:%s next:%s' % (self.socket_error,s))
                    self.set_status('01')
                    time.sleep(s)
            else:
                s = self.WATCH(self.status != '11')
                log.warn('status:11 next:%s' % s)
                self.set_status('11')
                time.sleep(s)
                continue


    def run(self):
        pid = os.fork()
        if pid == 0:
            self.main_process()
        else:
            os._exit(0)



if __name__ == '__main__':
    s = SshClient(_connect)
    s.run()
