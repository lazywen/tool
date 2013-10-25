#!/usr/bin/python
#-*- coding: utf-8 -*-

import asyncore
import logging


class EchoServer(asyncore.dispatcher):

    def __init__(self, addr):
        self.logger = logging.getLogger('\033[91mEchoServer\033[0m')
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(addr)
        self.addr = self.socket.getsockname()
        self.logger.debug('blinding to %s', self.addr)
        self.listen(1)
        return

    def handle_accept(self):
        client_info = self.accept()
        self.logger.debug('handle_accept() -> %s', client_info[1])
        EchoHandler(sock=client_info[0])
        self.handle_close()
        return

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return


class EchoHandler(asyncore.dispatcher):

    def __init__(self, sock, chunk_size=256):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('\033[92mEchoHandler\033[0m')
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = []
        return

    def writable(self):
        response = bool(self.data_to_write)
        self.logger.debug('writable() -> %s', response)
        return response

    def handle_write(self):
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('handle_write() -> (%s) %r', sent, data[:sent])

        if not self.writable():
            self.handle_close()

    def handle_read(self):
        data = self.recv(self.chunk_size)
        self.logger.debug('handle_read() -> (%d) %r', len(data), data)
        self.data_to_write.insert(0, data)

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()


class EchoClient(asyncore.dispatcher):

    def __init__(self, host, port, msg, chunk_size=128):
        self.msg = msg
        self.to_send = msg
        self.received_data = []
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('\033[93mEchoClient\033[0m')
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger.debug('connecting to %s', (host, port))
        self.connect((host, port))
        return
    
    def handle_connect(self):
        self.logger.debug('handle_connect()')

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        received_msg = ''.join(self.received_data)

        if received_msg == self.msg:
            self.logger.debug('received copy of message')
        else:
            self.logger.debug('err in transmission')
            self.logger.debug('expected "%s"', self.msg)
            self.logger.debug('received "%s"', received_msg)

    def writable(self):
        self.logger.debug('writable() -> %s', bool(self.to_send))
        return bool(self.to_send)

    def readable(self):
        self.logger.debug('readable() -> True ~~')
        return True

    def handle_write(self):
        sent = self.send(self.to_send[:self.chunk_size])
        self.logger.debug('handle_write() -> (%d) %r', sent, self.to_send[:sent])
        self.to_send = self.to_send[sent:]

    def handle_read(self):
        data = self.recv(self.chunk_size)
        self.logger.debug('handle_read() -> (%d) %r',
            len(data), data)
        self.received_data.append(data)


if __name__ == '__main__':
    import socket

    logging.basicConfig(
                level = logging.DEBUG,
                format = '%(name)-11s: %(message)s',
            )

    addr = ('localhost', 0)
    server = EchoServer(addr)
    ip, port = server.addr
    msg = open('msg.txt').read()
    logging.info('total message length: %d bytes', len(msg))

    client = EchoClient(ip, port, msg=msg)
    asyncore.loop()
