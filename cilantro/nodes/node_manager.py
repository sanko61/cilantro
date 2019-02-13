import time
import asyncio
import math
from collections import defaultdict
from cilantro.logger import get_logger
from cilantro.constants.zmq_filters import *
from cilantro.protocol.comm.lsocket import LSocketBase
from cilantro.storage.vkbook import VKBook
from cilantro.storage.state import StateDriver
from cilantro.nodes.masternode.mn_api import StorageDriver
from cilantro.storage.redis import SafeRedisMeta
from cilantro.storage.mongo import MDB
from cilantro.nodes.masternode.master_store import MasterOps
from cilantro.messages.block_data.block_data import BlockData
from cilantro.messages.block_data.block_metadata import BlockMetaData
from cilantro.messages.block_data.state_update import BlockIndexRequest, BlockIndexReply, BlockDataRequest, BlockDataReply


class NodeManager:
    def __init__(self, verifying_key: str, pub_socket: LSocketBase, router_socket: LSocketBase, is_master=True):
        self.log = get_logger("Node Manager")

        # infra input
        self.pub, self.router = pub_socket, router_socket
        self.verifying_key = verifying_key

        # Node type
        self.verify_db_state(is_master)

        # catchup state
        self.is_caught_up = False

        # Timers
        self.IDX_REPLY_TIMEOUT = 20
        self.TIMEOUT_CHECK_INTERVAL = 1
        self.timeout_catchup = time.time()
        self.timeout_fut = None

        # block info
        self.curr_hash, self.curr_num = StateDriver.get_latest_block_info()

    def verify_db_state(self, is_master):
        """
        Sync block and state DB if either is out of sync.
        :return:
        """
        if is_master:
            latest_blk_num = StorageDriver.get_latest_block_num()
            latest_state_num = StateDriver.get_latest_block_num()
            if latest_blk_num < latest_state_num:
                # TODO - assert and quit
                self.log.fatal("Block DB block - {} is behind StateDriver block - {}. Cannot handle"
                               .format(latest_blk_num, latest_state_num))
                # we need to rebuild state from scratch
                latest_state_num = 0
                SafeRedisMeta.flushdb()

            if latest_blk_num > latest_state_num:
                self.log.info("StateDriver block num {} is behind DB block num {}"
                              .format(latest_state_num, latest_blk_num))
                while latest_state_num < latest_blk_num:
                    latest_state_num = latest_state_num + 1
                    # TODO get nth full block wont work for now in distributed storage
                    blk_dict = StorageDriver.get_nth_full_block(given_bnum=latest_state_num)
                    if '_id' in blk_dict:
                        del blk_dict['_id']
                    block = BlockData.from_dict(blk_dict)
                    StateDriver.update_with_block(block = block)
            self.log.info("Verify StateDriver num {} StorageDriver num {}".format(latest_state_num, latest_blk_num))


class Catchup(NodeManager):
    pass


class Comm(NodeManager):
    pass

