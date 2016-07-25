#!/usr/bin/env python

import time
import logging

import bcrypt

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import set_path
from tilde.core.settings import settings
from tilde.core.api import API
import tilde.core.model as model
from tilde.berlinium import Async_Connection, add_redirection


logging.basicConfig(level=logging.INFO)

Tilde = API()
USER, PASS = 'test', 'test'
settings['debug_regime'] = False

class TildeGUIProvider:
    @staticmethod
    def login(req, client_id, db_session):
        result, error = None, None
        if not isinstance(req, dict): return result, 'Invalid request!'

        user = req.get('user')
        pwhash = req.get('pass', '')
        pwhash = pwhash.encode('ascii')

        pass_match = False
        try: pass_match = (pwhash == bcrypt.hashpw(PASS.encode('ascii'), pwhash))
        except: pass

        if user != USER or not pass_match:
            return result, 'Unauthorized!'
        Connection.Clients[client_id].authorized = True

        return "OK", None

    @staticmethod
    def sleep(req, client_id, db_session):
        result, error = '', None
        try: req = float(req)
        except: return result, 'Not a number!'

        time.sleep(req)

        result = Tilde.count(db_session)

        return result, error


if __name__ == "__main__":
    Connection = Async_Connection # test with: select * from pg_stat_activity;
    Connection.GUIProvider = TildeGUIProvider
    DuplexRouter = SockJSRouter(Connection)

    application = web.Application(
        add_redirection(DuplexRouter.urls, settings['gui_url']),
        debug = True if logging.getLogger().getEffectiveLevel()==logging.DEBUG or settings['debug_regime'] else False
    )
    application.listen(settings['webport'], address='0.0.0.0')

    logging.info("DB engine is %s" % settings['db']['engine'])
    logging.info("Connections are %s" % Connection.Type)
    logging.info("Server started")

    try: ioloop.IOLoop.instance().start()
    except KeyboardInterrupt: pass
