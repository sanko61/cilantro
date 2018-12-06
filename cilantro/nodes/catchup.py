import asyncio, zmq.asyncio, zmq
from cilantro.logger import get_logger
from cilantro.constants.zmq_filters import *

from cilantro.messages.block_data.block_data import BlockData, BlockMetaData
from cilantro.messages.block_data.state_update import BlockIndexRequest, StateUpdateReply

from cilantro.storage.state import StateDriver
from cilantro.storage.vkbook import VKBook
from cilantro.nodes.masternode.mn_api import StorageDriver
from cilantro.protocol.reactor.lsocket import LSocket

from typing import List, Union


class CatchupManager:
    def __init__(self, verifying_key: str, pub_socket: LSocket, router: LSocket, store_full_blocks=True):
        self.pub, self.router = pub_socket, router
        self.verifying_key = verifying_key
        self.store_full_blocks = store_full_blocks
        self.log = get_logger("CatchupManager")
        self.all_masters = set(VKBook.get_masternodes()) - set(self.verifying_key)

    def recv_state_update_req(self, request: SomeRequestType):
        assert self.store_full_blocks, "Must be able to store full blocks to reply to state update requests"
        # TODO reply properly

    def send_index_fetch_req(self):
        curr_hash = StateDriver.get_latest_block_hash()
        self.log.info("Requesting fetch requests from masternode with current block hash {}".format(curr_hash))

        req = BlockIndexRequest.create(block_hash=curr_hash)
        self.pub.send_msg(req, header=MASTER_MASTER_FILTER.encode())

    def recv_index_fetch_req(self, request: BlockIndexRequest):
        # TODO handle
        pass

    def recv_index_fetch_reply(self, reply: SomeReplyType):
        # TODO what to do here?
        pass

    def request_block_data(self, mn_vk: str, block_hashes: Union[str, List[str]]):
        if type(block_hashes) is str:
            block_hashes = [block_hashes]

        # request block hash via router socket with masternode vks
        msg = None  # TODO build foreal
        self.router.send_msg(msg, header=mn_vk.encode())

