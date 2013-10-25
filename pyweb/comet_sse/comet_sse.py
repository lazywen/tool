import time
import logging
import tornado.ioloop
import tornado.web
import tornado.options

#tornado.options.options['logging'] = 'info'

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")
        self.write("Hello, world")
        self.render("comet.html")

class SSEResHandler(tornado.web.RequestHandler):
    def get(self):
        last = self.request.headers.get('Last-Event-ID', None)
        print last
        #for i in xrange(10):
        self.set_header("Content-Type", "text/event-stream")
        if last:
            self.write("id: %s\n" % str(int(last)+1))
            self.write("data: %s\n\n" % str(int(last)+1))
        else:
            self.write("id: %s\n" % 1)
            self.write("data: %s\n\n" % 'good')
        time.sleep(4)
        self.write("data: %s\n\n" % 'good')
        #self.write("id: %s\n" % 1)
        #self.write("data: %s\n\n" % 'good')
        #self.flush()
        #self.write("id: %s\n" % 2)
        #self.write("data: %s\n\n" % 'bad')
        #self.flush()
        #time.sleep(1)

class CometHandler(tornado.web.RequestHandler):
    def get(self):
        print 'get comet'
        for i in xrange(10):
            self.write(str(i))
            #self.write(raw_input('>>'))
            self.flush()
            time.sleep(1)

class SSEHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("sse.html")

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/s", SSEHandler),
    (r"/comet", CometHandler),
    (r"/sse", SSEResHandler),
], debug=True)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
