#!/usr/bin/env python
# coding: utf-8


from pexpect import *
import pexpect
import time
import sys
import readline

server_list = (
    #(host,user,password),

    ('172.100.101.6', 'lishiwen', '123456'),
    ('172.100.101.14', 'lishiwen', '19880921'),
)


readline.parse_and_bind('set editing-mode vi')
__all__ = ['ExceptionPxssh', 'pxssh']

# Exception classes used by this module.
class ExceptionPxssh(ExceptionPexpect):
    """Raised for pxssh exceptions.
    """

class pxssh (spawn):

    def __init__ (self, timeout=30, maxread=2000, searchwindowsize=None, logfile=None, cwd=None, env=None):
        spawn.__init__(self, None, timeout=timeout, maxread=maxread, searchwindowsize=searchwindowsize, logfile=logfile, cwd=cwd, env=env)

        self.name = '<pxssh>'
        
        self.UNIQUE_PROMPT = "\[PEXPECT\][\$\#] "
        self.PROMPT = self.UNIQUE_PROMPT

        self.PROMPT_SET_SH = "PS1='[PEXPECT]\$ '"
        self.PROMPT_SET_CSH = "set prompt='[PEXPECT]\$ '"
        self.SSH_OPTS = "-o'RSAAuthentication=no' -o 'PubkeyAuthentication=no'"
        self.force_password = False
        self.auto_prompt_reset = True 

    def levenshtein_distance(self, a,b):

        n, m = len(a), len(b)
        if n > m:
            a,b = b,a
            n,m = m,n
        current = range(n+1)
        for i in range(1,m+1):
            previous, current = current, [i]+[0]*n
            for j in range(1,n+1):
                add, delete = previous[j]+1, current[j-1]+1
                change = previous[j-1]
                if a[j-1] != b[i-1]:
                    change = change + 1
                current[j] = min(add, delete, change)
        return current[n]

    def synch_original_prompt (self):


        self.sendline()
        time.sleep(0.5)
        self.read_nonblocking(size=10000,timeout=1) # GAS: Clear out the cache before getting the prompt
        time.sleep(0.1)
        self.sendline()
        time.sleep(0.5)
        x = self.read_nonblocking(size=1000,timeout=1)
        time.sleep(0.1)
        self.sendline()
        time.sleep(0.5)
        a = self.read_nonblocking(size=1000,timeout=1)
        time.sleep(0.1)
        self.sendline()
        time.sleep(0.5)
        b = self.read_nonblocking(size=1000,timeout=1)
        ld = self.levenshtein_distance(a,b)
        len_a = len(a)
        if len_a == 0:
            return False
        if float(ld)/len_a < 0.4:
            return True
        return False

    def login (self,server,username,password='',terminal_type='ansi',original_prompt=r"[#$]",login_timeout=10,port=None,auto_prompt_reset=True):

        ssh_options = '-q'
        if self.force_password:
            ssh_options = ssh_options + ' ' + self.SSH_OPTS
        if port is not None:
            ssh_options = ssh_options + ' -p %s'%(str(port))
        cmd = "ssh %s -l %s %s" % (ssh_options, username, server)

        # This does not distinguish between a remote server 'password' prompt
        # and a local ssh 'passphrase' prompt (for unlocking a private key).
        spawn._spawn(self, cmd)
        i = self.expect(["(?i)are you sure you want to continue connecting", original_prompt, "(?i)(?:password)|(?:passphrase for key)", "(?i)permission denied", "(?i)terminal type", TIMEOUT, "(?i)connection closed by remote host"], timeout=login_timeout)

        # First phase
        if i==0: 
            # New certificate -- always accept it.
            # This is what you get if SSH does not have the remote host's
            # public key stored in the 'known_hosts' cache.
            self.sendline("yes")
            i = self.expect(["(?i)are you sure you want to continue connecting", original_prompt, "(?i)(?:password)|(?:passphrase for key)", "(?i)permission denied", "(?i)terminal type", TIMEOUT])
        if i==2: # password or passphrase
            self.sendline(password)
            i = self.expect(["(?i)are you sure you want to continue connecting", original_prompt, "(?i)(?:password)|(?:passphrase for key)", "(?i)permission denied", "(?i)terminal type", TIMEOUT])
        if i==4:
            self.sendline(terminal_type)
            i = self.expect(["(?i)are you sure you want to continue connecting", original_prompt, "(?i)(?:password)|(?:passphrase for key)", "(?i)permission denied", "(?i)terminal type", TIMEOUT])

        if i==0:
            self.close()
            raise ExceptionPxssh ('Weird error. Got "are you sure" prompt twice.')
        elif i==1: # can occur if you have a public key pair set to authenticate. 
            pass
        elif i==2: # password prompt again
            self.close()
            raise ExceptionPxssh ('password refused')
        elif i==3: # permission denied -- password was bad.
            self.close()
            raise ExceptionPxssh ('permission denied')
        elif i==4: # terminal type again? WTF?
            self.close()
            raise ExceptionPxssh ('Weird error. Got "terminal type" prompt twice.')
        elif i==5: # Timeout
            pass
        elif i==6: # Connection closed by remote host
            self.close()
            raise ExceptionPxssh ('connection closed')
        else: # Unexpected 
            self.close()
            raise ExceptionPxssh ('unexpected login response')
        if not self.synch_original_prompt():
            self.close()
            raise ExceptionPxssh ('could not synchronize with original prompt')
        if auto_prompt_reset:
            if not self.set_unique_prompt():
                self.close()
                raise ExceptionPxssh ('could not set shell prompt\n'+self.before)
        return True

    def logout (self):


        self.sendline("exit")
        index = self.expect([EOF, "(?i)there are stopped jobs"])
        if index==1:
            self.sendline("exit")
            self.expect(EOF)
        self.close()

    def prompt (self, timeout=20):


        i = self.expect([self.PROMPT, TIMEOUT], timeout=timeout)
        if i==1:
            return False
        return True
        
    def set_unique_prompt (self):


        self.sendline ("unset PROMPT_COMMAND")
        self.sendline (self.PROMPT_SET_SH) # sh-style
        i = self.expect ([TIMEOUT, self.PROMPT], timeout=10)
        if i == 0: # csh-style
            self.sendline (self.PROMPT_SET_CSH)
            i = self.expect ([TIMEOUT, self.PROMPT], timeout=10)
            if i == 0:
                return False
        return True

def try_login(server):
    i = 0
    while(i < 3):
        try:
            s = pxssh()
            s.login(server[0], server[1], server[2])
            return s
        except:
            i += 1
    print "can not connecting to server %s" % server[0]
    sys.exit(2)
    


def ssh_login(server_list):
    server_ssh ={}
    if not server_list:
        print "error: needs at least one server!"
        sys.exit(2)
    for server in server_list:
#        try:
#            s = pxssh()
#            s.login(server[0], server[1], server[2])
#        except:
#            print "can not connecting to server %s" % server[0]
#            sys.exit(2)
#        server_ssh[server[0]] = s
        server_ssh[server[0]] = try_login(server)
    return server_ssh
    
def ssh_sendline(server_ssh, cmd):
    for server in server_ssh:
        s = server_ssh[server]
        s.sendline(cmd)
        s.prompt()
        print "********** %s **********\n%s\n" % (server,s.before)

def ssh_logout(server_ssh):
    for server in server_ssh:
        server_ssh[server].logout()

def main():
    server_ssh = ssh_login(server_list)
    print 'login success!'
    while(1):
        try:
            cmd = raw_input('> ')
        except (IOError,EOFError,KeyboardInterrupt),e:
            ssh_logout(server_ssh)
            print '\nbye~'
            return
        if not cmd:
            continue
        if cmd == 'exit' or cmd =='logout':
            ssh_logout(server_ssh)
            print '\nbye~'
            return
        ssh_sendline(server_ssh, cmd)

if __name__ == '__main__':
    pass
