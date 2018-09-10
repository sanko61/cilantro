from cilantro.logger import get_logger
from cilantro.protocol.overlay.interface import OverlayInterface

import asyncio
import os
from cilantro.protocol import wallet

class BaseNode():

    def __init__(self, ip, signing_key, name='Node'):

        self.log = get_logger(name)
        self.ip = ip
        self.name = name

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.context = zmq.asyncio.Context()

        self.signing_key = signing_key
        self.verifying_key = wallet.get_vk(self.signing_key)
        self.log.important3("Node with vk {} has ip {}".format(self.verifying_key, os.getenv("HOST_IP")))

        self.log.notice("Starting overlay service")
        self.overlay_proc = LProcess(target=OverlayInterface.start_service, args=(signing_key,))
        self.overlay_proc.start()

        self.pub_socket = ZmqAPI.add_pub(self.ip)
        self.dealers = []
        self.sockets = []  # will they be 1-1 correspondence with tasks: order and number??
        self.tasks = []


    def teardown(self):
        """
        Tears down the application stack.
        """
        self.log.important("Tearing down application")
        if hasattr(self, 'server'):
            self.server.terminate()
        # sub-classes need to derive this
        self._teardown()
