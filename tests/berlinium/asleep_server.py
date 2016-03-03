#!/usr/bin/env python

import time
import logging

from sqlalchemy import text

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import set_path
from tilde.core.settings import settings
from tilde.core.api import API
from tilde.berlinium import Async_Connection


logging.basicConfig(level=logging.INFO)

Tilde = API()
settings['debug_regime'] = False

class SleepTester:
    @staticmethod
    def login(req, client_id, db_session):
        Connection.Clients[client_id].authorized = True
        return "OK", None

    @staticmethod
    def sleep(req, client_id, db_session):
        result, error = '', None
        try: req = float(req)
        except: return result, 'Not a number!'

        current_engine = db_session.get_bind()

        if settings['db']['engine'] == 'postgresql':
            current_engine.execute(text('SELECT pg_sleep(:i)'), **{'i': req})

        elif settings['db']['engine'] == 'sqlite':
            conn = current_engine.raw_connection()
            conn.create_function("sq_sleep", 1, time.sleep)
            c = conn.cursor()
            c.execute('SELECT sq_sleep(%s)' % req)

        result = Tilde.count(db_session)
        return result, error

if __name__ == "__main__":
    Connection = Async_Connection
    Connection.GUIProvider = SleepTester
    DuplexRouter = SockJSRouter(Connection)
    application = web.Application(DuplexRouter.urls, debug=False)
    application.listen(settings['webport'], address='0.0.0.0')

    logging.info("DB is %s" % settings['db']['engine'])
    logging.info("Connections are %s" % Connection.Type)
    logging.info("Server started")

    ioloop.IOLoop.instance().start()
