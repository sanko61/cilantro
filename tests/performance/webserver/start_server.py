from multiprocessing import Queue
from sanic import Sanic
from cilantro.logger.base import get_logger
from cilantro.nodes.masternode.webserver import start_webserver

app = Sanic(__name__)
log = get_logger(__name__)

import pyximport; pyximport.install()
if not app.config.REQUEST_MAX_SIZE:
    app.config.update({
        'REQUEST_MAX_SIZE': 5,
        'REQUEST_TIMEOUT': 5
    })
start_webserver(Queue())
