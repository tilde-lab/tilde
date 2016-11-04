#!/usr/bin/env python

import sys
import time
import logging

import websocket

import ujson as json

import set_path
from tilde.core.settings import settings


logging.basicConfig(level=logging.INFO)
START_TIME = time.time()

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
        ws.send(json.dumps({'act': 'login', 'req': {'settings':{'cols': [1, 1002, 1501, 1502, 1503]}}}))

    @classmethod
    def on_message(self, ws, message):
        logging.debug("Received: %s" % message[:100])
        message = json.loads(message)
    
        if message['act'] == 'login':
            ws.send(json.dumps({'act': 'tags', 'req': {}}))

        elif message['act'] == 'tags':
            ws.send(json.dumps({'act': 'browse', 'req': {'tids': [2]}}))

        elif message['act'] == 'browse':
            ws.send(json.dumps({'act': 'summary', 'req': {'datahash': 'QZAKBZE26UUMBYJBDDG7XBNYN5IZJJAAW3VI5OJ2CJPXCCI'}}))

        elif message['act'] == 'summary':
            ws.send(json.dumps({'act': 'estory', 'req': {'datahash': 'OLRUC4GMJKHKOFIEQIDNQBJDII4UH5WQCGQRO5MXD36GSCI'}}))

        elif message['act'] == 'estory':
            logging.info("Client done in: %1.2f sc" % (time.time() - START_TIME))
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
