import socket
import time
import sys

msgs = (
        #'a',
        #'b',
        #'c',
        #'d',
        'e',
        )

server_address = ('localhost', 8080)

socks = (
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            #socket.socket(socket.AF_INET, socket.SOCK_STREAM),
        )

print 'connecting to %s port %s' % server_address
for s in socks:
    s.connect(server_address)

for msg in msgs:
    for s in socks:
        print '%s sending %s' % (s.getpeername(), msg)
        s.send(msg)
        time.sleep(0.4)
        s.send('coming')
        time.sleep(0.2)

    for s in socks:
        data = s.recv(1024)
        print '%s received %s' % (s.getpeername(), data)

        if not data:
            print 'cloing socket', s.getpeername()
            s.close()
