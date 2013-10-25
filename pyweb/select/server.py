import select
import socket
import sys
import Queue
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

server_address = ('localhost', 8080)
print >> sys.stderr, 'starting up on %s port %s' % server_address
server.bind(server_address)
server.listen(1)

inputs = [server]
outputs = []
msg_queues = {}

while inputs:
    print >> sys.stderr, '\n\nwaiting for the next event *******************************************'
    readable, writable, exceptional = select.select(
                inputs,
                outputs,
                inputs,
            )
    print 'readable, writable, exceptional'
    print readable, writable, exceptional
    print '--------------------------------------------------------------------------'
    print 'inputs, outputs, msg_queues'
    print inputs, outputs, msg_queues

    for s in writable:
        try:
            next_msg = msg_queues[s].get_nowait()
        except Queue.Empty:
            print >> sys.stderr, s.getpeername(), 'queue empty'
            outputs.remove(s)
        else:
            print >> sys.stderr, 'sending %s to %s' % (next_msg, s.getpeername())
            s.send(next_msg)
            time.sleep(0.2)

    for s in readable:
        if s is server:
            connection, client_addr = s.accept()
            print >> sys.stderr, 'connection from', client_addr

            connection.setblocking(0)
            inputs.append(connection)

            msg_queues[connection] = Queue.Queue()

        else:
            data = s.recv(1024)
            if data:
                print >> sys.stderr, 'received %s from %s' % (data, s.getpeername())
                msg_queues[s].put(data)

                if s not in outputs:
                    outputs.append(s)

            else:
                print >> sys.stderr, 'closing', client_addr
                if s in outputs:
                    outputs.remove(s)
                inputs.remove(s)
                s.close()

                del msg_queues[s]

    for s in exceptional:
        print >> sys.stderr, 'exception condition on', s.getpeername()
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del msg_queues[s]
