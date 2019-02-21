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

            # strict no no
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
    def trigger_catchup(self, ignore=False):
        """
        :param ignore: #TODO not clear
        :return:
        """
        self.log.important3("-----RUN-----")
        # check if catch up is already running
        if ignore and self.is_catchup_done():
            self.log.warning("Already caught up. Ignoring to run it again.")
            return

        # first reset state variables
        self.node_idx_reply_set.clear()
        self.is_caught_up = False
        # self.curr_hash, self.curr_num = StateDriver.get_latest_block_info()
        # self.target_blk_num = self.curr_num
        # self.awaited_blknum = None

        # starting phase I
        self.timeout_catchup = time.time()
        self.send_block_idx_req()

        self._reset_timeout_fut()
        # first time wait longer than usual
        time.sleep(3 * TIMEOUT_CHECK_INTERVAL)
        self.timeout_fut = asyncio.ensure_future(self._check_timeout())
        self.log.important2("Running catchup!")
        self.dump_debug_info(lnum = 111)

    def process_block_index_request(self):
        pass

    def process_block_index_reply(self):
        pass

    def process_block_data_request(self):
        pass

    def process_block_data_reply(self):
        pass


class Comm(Catchup):
    def send_block_idx_req(self, sender_hash):
        """
        API: with given a current hash API request's Master to send list of blocks after that hash.
        Multi-casting BlockIndexRequests to all master nodes with current block hash
        :return:
        """
        self.log.info("Multi cast BlockIndexRequests to all MN with current block hash {}".format(self.curr_hash))
        request = BlockIndexRequest.create(block_hash=sender_hash)
        self.pub.send_msg(request, header=CATCHUP_MN_DN_FILTER.encode())

    def send_block_data_req(self, mn_vk, req_blk_num):
        self.log.info("Unicast BlockDateRequests to masternode owner with current block num {} key {}"
                      .format(req_blk_num, mn_vk))
        req = BlockDataRequest.create(block_num = req_blk_num)
        self.router.send_msg(req, header=mn_vk.encode())

    def recv_block_idx_req(self, requester_vk: str, request: BlockIndexRequest):
        self.log.debugv("Got block index request from sender {} requesting block hash {} my_vk {}"
                        .format(requester_vk, request.block_hash, self.verifying_key))

        if requester_vk == self.verifying_key:
            self.log.debugv("received request from myself dropping the req")
            return
        self.process_block_index_request()

    def recv_block_idx_reply(self, sender_vk: str, reply: BlockIndexReply):
        self.process_block_index_reply()
        pass

    def recv_block_data_reply(self, reply: BlockData):
        self.process_block_data_reply()
        pass

