
# implementation of blocking websocket connections
# with (customly) pooled DB sessions

import logging

from tornado import ioloop
from sockjs.tornado import SockJSConnection

import ujson as json

from tilde.berlinium.impl import GUIProviderMockup, Client
from tilde.core.settings import settings, connect_database


class Connection(SockJSConnection):
    Type = 'blocking'
    Clients = {}
    GUIProvider = GUIProviderMockup

    def on_open(self, info):
        self.Clients[ getattr(self.session, 'session_id', self.session.__hash__()) ] = Client()
        logging.info("Server connected %s-th client" % len(self.Clients))

    def on_message(self, message):
        logging.debug("Server got: %s" % message)
        try:
            message = json.loads(message)
            message.get('act')
        except: return self.send(json.dumps({'act':'login', 'error':'Not a valid JSON!'}))

        frame = {
            'client_id': getattr(self.session, 'session_id', self.session.__hash__()),
            'act': message.get('act', 'unknown'),
            'req': message.get('req', ''),
            'error': '',
            'result': ''
        }

        # security check: a client must be authorized
        if not self.Clients[frame['client_id']].authorized and frame['act'] != 'login': return self.close()

        if not hasattr(self.GUIProvider, frame['act']):
            frame['error'] = 'No server handler for action: %s' % frame['act']
            return self.respond(frame)

        if not Connection.Clients[frame['client_id']].db: Connection.Clients[frame['client_id']].db = connect_database(settings, default_actions=False, no_pooling=True)

        frame['result'], frame['error'] = getattr(self.GUIProvider, frame['act'])( frame['req'], frame['client_id'], Connection.Clients[frame['client_id']].db )
        self.respond(frame)

    def respond(self, output):
        del output['client_id']
        if not output['error'] and not output['result']:
            output['error'] = "Handler %s has returned an empty result!" % output['act']

        logging.debug("Server responds: %s" % output)
        self.send(json.dumps(output))

    def on_close(self):
        logging.info("Server will close connection with %s-th client" % len(self.Clients))
        client_id = getattr(self.session, 'session_id', self.session.__hash__())

        # must explicitly close db connection
        try:
            self.Clients[client_id].db.close()
            self.Clients[client_id].db = None
        except: pass
        del self.Clients[client_id]
