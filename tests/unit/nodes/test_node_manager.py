from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('4-4-4.json')

from unittest import TestCase
from unittest.mock import MagicMock, patch

from cilantro.nodes.node_manager import NodeManager
from cilantro.storage.state import StateDriver
from cilantro.storage.redis import SafeRedis
from cilantro.nodes.masternode.mn_api import StorageDriver
from cilantro.nodes.masternode.master_store import MasterOps
from cilantro.storage.mongo import MDB

from cilantro.messages.block_data.block_data import *
from cilantro.messages.block_data.state_update import *
from cilantro.messages.block_data.block_metadata import *

import asyncio, time
from cilantro.protocol import wallet

SK = 'A' * 64
VK = wallet.get_vk(SK)


class TestNodeManager(TestCase):

    @classmethod
    def setUpClass(cls):
        MasterOps.init_master(key=SK)

    def setUp(self):
        MDB.reset_db()
        StateDriver.set_latest_block_info(block_hash=GENESIS_BLOCK_HASH, block_num=0)
        # TODO how to rest Mongo between runs?
        self.manager = None
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def tearDown(self):
        if self.manager.timeout_fut and not self.manager.timeout_fut.done():
            self.manager.timeout_fut.cancel()
        asyncio.get_event_loop().close()

    def _build_manager(self, vk=VK, store_blocks=True) -> NodeManager:
        pub, router = MagicMock(), MagicMock()
        m = NodeManager(verifying_key=vk, pub_socket=pub, router_socket=router, is_master=store_blocks)
        self.manager = m
        return m

    def _assert_router_called_with_msg(self, cm: NodeManager, msg: MessageBase, possible_headers):
        assert type(possible_headers) in (tuple, bytes), "Header must be a tuple of bytes, or a byte obj"
        for call_arg in cm.router.send_msg.call_args_list:
            args, kwargs = call_arg
            self.assertEqual(args[0], msg)
            if type(possible_headers) is tuple:
                self.assertTrue(kwargs['header'] in possible_headers)
            else:
                self.assertEqual(kwargs['header'], possible_headers)

    def test_init(self):
        m = self._build_manager()

        self.assertEqual(m.curr_hash, StateDriver.get_latest_block_hash())
        self.assertEqual(m.curr_num, StateDriver.get_latest_block_num())


if __name__ == "__main__":
    import unittest
    unittest.main()
