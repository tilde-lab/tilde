#!/usr/bin/env python

import sys
import time
import logging

import bcrypt
import websocket

try: import ujson as json
except ImportError: import json

import set_path
from tilde.core.settings import settings


logging.basicConfig(level=logging.INFO)

START_TIME = time.time()

USER, PASS = 'test', 'test'

class RespHandler(object):
    @classmethod
    def on_error(self, ws, error):
        logging.error(error)

    @classmethod
    def on_close(self, ws):
        logging.debug("Closed")
        ws.close()

    @classmethod
    def on_open(self, ws):
        logging.debug("Opened")
        pwhash = bcrypt.hashpw(PASS.encode('ascii'), bcrypt.gensalt())
        ws.send(json.dumps({'act': 'login', 'req': {'user': USER, 'pass': pwhash}}))

    @classmethod
    def on_message(self, ws, message):
        logging.debug("Received: %s" % message[:100])
        message = json.loads(message)
    
        if message['act'] == 'login':
            if message['result'] == 'OK':
                ws.send(json.dumps({'act': 'sleep', 'req': 3}))
            else:
                logging.error("Auth failed!")
                sys.exit(1)

        elif message['act'] == 'sleep':
            logging.info("Client done in %1.2f sc" % (time.time() - START_TIME))
            ws.close()
            sys.exit(0)


if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://localhost:%s/websocket" % settings['webport'],
                                on_open = RespHandler.on_open,
                                on_message = RespHandler.on_message,
                                on_error = RespHandler.on_error,
                                on_close = RespHandler.on_close)
    logging.debug("Started")
    ws.run_forever()
