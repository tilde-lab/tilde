#!/usr/bin/env python
import time
import logging

import bcrypt

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import set_path
from tilde.core.settings import settings, connect_database
from tilde.core.api import API
import tilde.core.model as model
from tilde.berlinium import Connection, add_redirection


logging.basicConfig(level=logging.DEBUG)

Tilde = API()
USER, PASS = 'test', 'test'
settings['debug_regime'] = False

class TildeGUIProvider:
    @staticmethod
    def login(req, session_id):
        result, error = None, None
        if not isinstance(req, dict): return result, 'Invalid request!'

        user = req.get('user')
        pwhash = req.get('pass', '')
        pwhash = pwhash.encode('ascii')

        pass_match = False
        try: pass_match = (pwhash == bcrypt.hashpw(PASS, pwhash))
        except: pass

        if user != USER or not pass_match:
            return result, 'Unauthorized!'
        Connection.Clients[session_id].authorized = True
        Connection.Clients[session_id].db = connect_database(settings, default_actions=False, scoped=True)
        return "OK", None

    @staticmethod
    def tags(req, session_id):
        result, error = [], None
        if not isinstance(req, dict): return result, 'Invalid request!'

        if not 'tids' in req: tids = None # NB json may contain nulls
        else: tids = req['tids']

        if not tids:
            for tid, cid, topic in Connection.Clients[session_id].db.query(model.uiTopic.tid, model.uiTopic.cid, model.uiTopic.topic).all():
                # TODO assure there are checksums for every tid
                try: match = [x for x in Tilde.hierarchy if x['cid'] == cid][0]
                except IndexError: return None, 'Schema and data do not match: different versions of code and database?'

                if not 'has_label' in match or not match['has_label']: continue

                sort = 1000 if not 'sort' in match else match['sort']

                ready_topic = {'tid': tid, 'topic': topic, 'sort': 0}

                for n, tag in enumerate(result):
                    if tag['category'] == match['category']:
                        result[n]['content'].append( ready_topic )
                        break
                else: result.append({'cid': match['cid'], 'category': match['category'], 'sort': sort, 'content': [ ready_topic ]})

            result.sort(key=lambda x: x['sort'])
            result = {'blocks': result, 'cats': Tilde.supercategories}

        return result, error

    @staticmethod
    def sleep(req, session_id):
        result, error = '', None
        try: req = float(req)
        except: return result, 'Not a number!'

        time.sleep(req)

        result = Tilde.count(Connection.Clients[session_id].db)

        return result, error

    @staticmethod
    def example(req, session_id):
        result, error = '', None
        return result, error

if __name__ == "__main__":
    Connection.GUIProvider = TildeGUIProvider
    DuplexRouter = SockJSRouter(Connection)

    application = web.Application(
        add_redirection(DuplexRouter.urls, settings['gui_url']),
        debug = True if logging.getLogger().getEffectiveLevel()==logging.DEBUG or settings['debug_regime'] else False
    )
    application.listen(settings['webport'], address='0.0.0.0')

    logging.debug("Server started")

    try: ioloop.IOLoop.instance().start()
    except KeyboardInterrupt: pass
