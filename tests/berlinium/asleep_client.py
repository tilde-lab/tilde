#!/usr/bin/env python
import time
import logging
import websocket
import json

import set_path
from tilde.core.settings import settings

logging.basicConfig(level=logging.DEBUG)
START_TIME = time.time()

class RespHandler(object):
    @classmethod
    def on_open(self, ws):
        logging.debug("Client connected")
        to_send = {'act': 'login'}
        ws.send(json.dumps(to_send))

    @classmethod
    def on_message(self, ws, message):
        logging.debug("Client got: %s" % message)
        message = json.loads(message)
        if message['act'] == 'login':
            to_send = {'act': 'sleep', 'req': 4}
            ws.send(json.dumps(to_send))
        else:
            logging.info("Client done in: %1.2f sc" % (time.time() - START_TIME))
            ws.close()

    @classmethod
    def on_error(self, ws, error):
        logging.debug(error)

    @classmethod
    def on_close(self, ws):
        logging.debug("Client finished")
        ws.close()

if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://localhost:%s/websocket" % settings['webport'],
                                on_open = RespHandler.on_open,
                                on_message = RespHandler.on_message,
                                on_error = RespHandler.on_error,
                                on_close = RespHandler.on_close)
    ws.run_forever()
