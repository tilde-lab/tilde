#!/usr/bin/env python
import json
import logging

from sqlalchemy import text

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import set_path
from tilde.core.settings import settings, connect_database
from tilde.core.api import API
from tilde.berlinium.async_impl import Connection


Tilde = API()
settings['db']['engine'] = 'postgresql'
settings['debug_regime'] = False

logging.basicConfig(level=logging.DEBUG)

class SleepTester:
    @staticmethod
    def login(req, session_id):
        result, error = '', None
        try: req = float(req)
        except: return result, 'Not a number!'

        Connection.Clients[session_id].db = connect_database(settings, default_actions=False, scoped=True)
        current_engine = Connection.Clients[session_id].db.get_bind()
        current_engine.execute(text('SELECT pg_sleep(:i)'), **{'i': req})
        result = Tilde.count(Connection.Clients[session_id].db)

        return result, error

if __name__ == "__main__":
    Connection.GUIProvider = SleepTester
    DuplexRouter = SockJSRouter(Connection)
    application = web.Application(DuplexRouter.urls, debug=False)
    application.listen(settings['webport'], address='0.0.0.0')

    logging.debug("Server started")

    try: ioloop.IOLoop.instance().start()
    except KeyboardInterrupt: pass
