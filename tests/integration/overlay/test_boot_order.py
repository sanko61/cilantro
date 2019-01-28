from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('2-2-2.json')
from vmnet.comm import file_listener
from vmnet.testcase import BaseTestCase
import unittest, time, random, vmnet, cilantro, asyncio, ujson as json
from os.path import join, dirname
from cilantro.utils.test.mp_test_case import vmnet_test, wrap_func
from cilantro.logger.base import get_logger
from cilantro.constants.testnet import TESTNET_MASTERNODES, TESTNET_DELEGATES, TESTNET_WITNESSES

def node(sk, idx, all_vks):
    from cilantro.nodes.factory import NodeFactory
    import os
    ip = os.getenv('NODE').split(',')[idx]
    if idx < 2:
        NodeFactory.run_masternode(sk, ip)
    elif idx < 4:
        NodeFactory.run_witness(sk, ip)
    elif idx < 6:
        NodeFactory.run_delegate(sk, ip)

    # from cilantro.constants.testnet import TESTNET_MASTERNODES
    # from cilantro.protocol.overlay.interface import OverlayInterface
    # from cilantro.constants.overlay_network import MIN_BOOTSTRAP_NODES
    # from cilantro.storage.vkbook import VKBook
    # from vmnet.comm import send_to_file
    # import asyncio, json, os, zmq
    # from cilantro.logger import get_logger
    # log = get_logger('MasterNode_{}'.format(idx))
    #
    # async def check():
    #     while True:
    #         await asyncio.sleep(1)
    #         if len(oi.authorized_nodes['*']) >= node_count:
    #             send_to_file(os.getenv('HOST_NAME'))
    #
    # async def connect():
    #     await asyncio.sleep(8)
    #     await asyncio.gather(*[oi.authenticate(all_ips[i], vk) for i, vk in enumerate(all_vks)])
    #
    # all_ips = os.getenv('NODE').split(',')
    #
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # ctx = zmq.asyncio.Context()
    # oi = OverlayInterface(TESTNET_MASTERNODES[idx]['sk'], loop=loop, ctx=ctx)
    # oi.tasks += [connect(), check()]
    # oi.start()

class TestBootOrder(BaseTestCase):

    log = get_logger(__name__)
    config_file = join(dirname(cilantro.__path__[0]), 'vmnet_configs', 'cilantro-nodes-6.json')
    enable_ui = False

    def callback(self, data):
        for node in data:
            self.nodes_complete.add(node)
        if self.nodes_complete == self.all_nodes:
            self.end_test()

    def timeout(self):
        self.assertEqual(self.nodes_complete, self.all_nodes)

    def test_boot_order(self):
        self.all_nodes = set(self.groups['node'])
        self.nodes_complete = set()
        nodes = [node for node in TESTNET_MASTERNODES + TESTNET_WITNESSES + TESTNET_DELEGATES]
        all_sks = [n['sk'] for n in nodes]
        all_vks = [n['vk'] for n in nodes]
        for i in range(len(self.all_nodes)):
            self.execute_python(self.groups['node'][i], wrap_func(node, all_sks[i], i, all_vks))

        file_listener(self, self.callback, self.timeout, 90)

if __name__ == '__main__':
    unittest.main()
