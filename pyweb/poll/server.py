import select
import socket 
import sys
import Queue

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

server_addr = ('localhost', 10000)
print 'starting up on %s port %s' % server_addr
server.bind(server_addr)
server.listen(5)

msg_queues = {}

TIMEOUT = 1000

READ_ONLY = (
        select.POLLIN |
        select.POLLPRI |
        select.POLLHUP |
        select.POLLERR
    )

READ_WRITE = READ_ONLY | select.POLLOUT
print READ_ONLY, READ_WRITE

poller = select.poll()
poller.register(server, READ_ONLY)

fd_to_socket = {server.fileno(): server,}

while True:
    print 'warting for the next event'
    events = poller.poll(TIMEOUT)

    for fd, flag in events:
        s = fd_to_socket[fd]

        if flag & (select.POLLIN | select.POLLPRI):

            if s is server:
                connection, client_addr = s.accept()
                print 'connection', client_addr
                connection.setblocking(0)
                fd_to_socket[connection.fileno()] = connection
                poller.register(connection, READ_ONLY)
                msg_queues[connection] = Queue.Queue()

            else:
                data = s.recv(1024)
                if data:
                    print 'recive %s from %s' % (data, s.getpeername())
                    msg_queues[s].put(data)
                    poller.modify(s, READ_WRITE)

                else:
                    print 'closing', client_addr
                    poller.unregister(s)
                    s.close()
                    del msg_queues[s]

        elif flag & select.POLLHUP:
            print 'closing', client_addr, '(HUP)'
            poller.unregister(s)
            s.close()

        elif flag & select.POLLOUT:
            try:
                next_msg = msg_queues[s].get_nowait()
            except Queue.Empty:
                print s.getpeername(), 'queue empty'
                poller.modify(s, READ_ONLY)
            else:
                print 'sending %s to %s' % (next_msg, s.getpeername())
                s.send(next_msg)

        elif flag & select.POLLERR:
            print 'exception on', s.getpeername()
            poller.unregister(s)
            s.close()
            del msg_queues[s]
