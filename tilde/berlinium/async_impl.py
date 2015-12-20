
# implementation of thread pool for async websocket connections

import logging
import threading
import multiprocessing
from functools import partial

from concurrent.futures import ThreadPoolExecutor

from tornado import ioloop
from sockjs.tornado import SockJSConnection

try: import ujson as json
except ImportError: import json


thread_pool = ThreadPoolExecutor(max_workers=5*multiprocessing.cpu_count())

class GUIProviderMockup:
    pass

class Client:
    def __init__(self):
        self.usettings = {}
        self.authorized = False
        self.db = None

class Connection(SockJSConnection):
    Clients = {}
    GUIProvider = GUIProviderMockup

    def on_open(self, info):
        self.Clients[ getattr(self.session, 'session_id', self.session.__hash__()) ] = Client()
        logging.debug("Server connected")

    def on_message(self, message):
        logging.debug("Server got: %s" % message)
        try:
            message = json.loads(message)
            message.get('act')
        except: return self.send(json.dumps({'error':'Not a valid JSON!'}))

        frame = { \
            'act': message.get('act', 'unknown'),
            'req': message.get('req', ''),
            'error': '',
            'result': '',
            'session': getattr(self.session, 'session_id', self.session.__hash__())
        }

        if not self.Clients[frame['session']].authorized and frame['act'] != 'login': return self.close()

        if not hasattr(self.GUIProvider, frame['act']):
            frame['error'] = 'No server handler for action: %s' % frame['act']
            return self.respond(frame)

        def worker(frame):
            frame['result'], frame['error'] = getattr(self.GUIProvider, frame['act'])( frame['req'], frame['session'] )
            return frame

        def callback(future):
            self.respond(future.result())

        thread_pool.submit( partial(worker, frame) ).add_done_callback( \
            lambda future: ioloop.IOLoop.instance().add_callback( \
                partial(callback, future)
            )
        )

    def respond(self, output):
        del output['session']
        if not output['error'] and not output['result']:
            output['error'] = "Handler %s has returned an empty result!" % output['act']

        logging.debug("Server responds: %s" % output)
        self.send(json.dumps(output))
        #self.close() # TODO?

    def on_close(self):
        session_id = getattr(self.session, 'session_id', self.session.__hash__())
        if self.Clients[session_id].db: self.Clients[session_id].db.close()
        del self.Clients[session_id]
        logging.debug("Server closed connection")
