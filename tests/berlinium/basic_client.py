#!/usr/bin/env python
import time
import logging
import bcrypt
import websocket

try: import ujson as json
except ImportError: import json

import set_path
from tilde.core.settings import settings


logging.basicConfig(level=logging.DEBUG)

START_TIME = time.time()

USER, PASS = 'test', 'test'

class RespHandler(object):
    @classmethod
    def on_open(self, ws):
        logging.debug("Opened")
        pwhash = bcrypt.hashpw(PASS, bcrypt.gensalt())
        to_send = {'act': 'login', 'req': {'user': USER, 'pass': pwhash}}
        ws.send(json.dumps(to_send))

    @classmethod
    def on_message(self, ws, message):
        logging.info("Received: %s" % message[:100])
        message = json.loads(message)
    
        if message['act'] == 'login':
            if message['result'] == 'OK':
                to_send = {'act': 'tags', 'req': {'tids':0}}
                ws.send(json.dumps(to_send))
            else:
                logging.info("Auth failed!")

        elif message['act'] == 'tags':
            logging.info(message['result'])
            to_send = {'act': 'sleep', 'req': 4}
            ws.send(json.dumps(to_send))

        elif message['act'] == 'sleep':
            logging.info("Client done in: %1.2f sc" % (time.time() - START_TIME))
            ws.close()

    @classmethod
    def on_error(self, ws, error):
        logging.error(error)

    @classmethod
    def on_close(self, ws):
        logging.debug("Closed")
        ws.close()


if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://localhost:%s/websocket" % settings['webport'],
                                on_open = RespHandler.on_open,
                                on_message = RespHandler.on_message,
                                on_error = RespHandler.on_error,
                                on_close = RespHandler.on_close)
    ws.run_forever()
