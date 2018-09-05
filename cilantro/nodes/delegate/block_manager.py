"""
    BlockManager  (main process of delegate)

    This should coordinate the resolution mechanism for inter-subblock conflicts.
    It will also stitch two subblocks into one subtree and send to master and other delegates for voting.
    And will send in its vote on other subtrees to master directly when received from other delegates

    It can also have a thin layer of row conflict info that can be used to push some transactions to next block if they are conflicting with transactions in flight
    It will rotate asking 16 sets of sub-block-builders to proceed.

    It will also get new block notifications from master and can update its thin layer caching
        ask next set of sub-block-builders to proceed
        communicate failed contracts to previous sub-block-builder (SBB) either to reject or repeat in next block
    manages a pool of 64 processes for SBB.
    also spawns a thread for overlay network

    Input:
      - responsible subtree (based on delegate ordering ??? constant until next election)

    need to decide whether this code will live in delegate.py under Delegate class or 
    Delegate class will contain this class as a data structure and manage this and other stuff
"""

from cilantro.storage.db import VKBook
from cilantro.nodes import BaseNode

MAX_BLOCKS = 4     # can be config parameter

# communication
# From master:
#   Drop witness(es) - list
#   Add witness(es) - list
#   New Block Notification
# From Delegate (BM)
#   Request Witness list
#   Request latest block hash  (can be combined with req witness list)
#   Request block data since hash
#   send sub-tree(i) with sig + data
#   Send sig for sub-tree(i)
#   send Ready ??

class BlockManager(BaseNode):

   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)

       # initialize
       self.current_hash = BlockStorageDriver.get_latest_block_hash()
       self.mn_indices = {}        # mn_vk  index
       self.sb_builders = {}       # index  process      # perhaps can be consolidated with the above ?

       self.num_mnodes = self.get_max_number_of_masternodes()
       # self.num_blocks = int(self.num_mnodes / MAX_SUB_BLOCK_BUILDERS + 1)
       self.num_blocks = MAX_BLOCKS if MAX_BLOCKS < self.num_mnodes
                                    else self.num_mnodes
       self.max_sb_builders = (int) (self.num_mnodes + self.num_blocks - 1)
                                    / self.num_blocks
       self.my_sb_index = self.get_my_index() % self.max_sb_builders

       # let's assume base node that tracks overlay process sets a flag to indicate it's boot ready
       # need to coordinate its boot state with overlay network
       # once boot ready, it needs to spawn 


   def run(self):
       
       # build task list first
       self.build_task_list()

   def build_task_list(self):
       
       # Add router socket - where do we listen to this ?? add
       socket = ZmqAPI.add_router(ip=self.ip) 
       self.sockets.append(socket)
       self.tasks.append(self._listen_to_router(socket))  

       # now build listening tasks to other delegate(s)
       for vk in VKBook.get_delegates():
           if vk != self.verifying_key:       # not to itself
               socket = ZmqAPI.add_sub(vk=vk, filter=DELEGATE_DELEGATE_FILTER)
               self.sockets.append(socket)
               self.tasks.append(self._sub_to_delegate(socket, vk))

       # first build master(s) listening tasks
       self.build_masternode_indices()  # builds mn_indices
       for vk, index in self.mn_indices:
           # ip = OverlayInterface::get_node_from_vk(vk)
           # sub connection
           socket = ZmqAPI.add_sub(vk=vk, filter=MASTERNODE_DELEGATE_FILTER, port=MN_NEW_BLOCK_PUB_PORT)
           self.sockets.append(socket)
           self.tasks.append(self._sub_to_master(socket, vk, index)

           # dealer connection
           socket = ZmqAPI.add_dealer(vk)
           self.dealers.append(socket)
           # self.tasks.append(self._dealer_to_master(socket, vk, index)
           
           # create sbb processes and sockets
           self.sbb_ports[index] = port = 6000 + index       # 6000 -> SBB_PORT 
           self.sb_builders[index] = Process(target=SubBlockBuilder,
                                             args=(self.signing_key, self.url,
                                                   self.sbb_ports[index], index))  # we probably don't need to pass port if we pass index
           self.sb_builders[index].start()
           socket = ctx.socket(socket_type=zmq.PAIR)
           socket.connect(url)
           self.sockets.append(socket)
           self.tasks.append(self._listen_to_sbb(socket, vk, index)
           # self.url = "ipc://{}-ReactorIPC-".format(name) + str(random.randint(0, pow(2, 16)))
           # url = "tcp://172.29.5.1:10200"
           

   def get_max_number_of_masternodes(self):
       return len(VKBook.get_masternodes())

   # assuming master set is fixed - need to build a table (key: vk, value: index)
   def build_masternode_indices(self):
       for index, vk in enumerate(VKBook.get_masternodes()):
          self.mn_indices[vk] = index
       
   def build_sbb_sockets(self):
      # make 
      for index in range(len(VKBook.get_masternodes())

   async def _listen_to_router(socket):

   async def _sub_to_delegate(socket, vk):
       # Events:
       # 1. publish sub-block

   async def _sub_to_master(socket, mn_vk, mn_index):
       # Events:
       # 1. New block notification

   async def _listen_to_sbb(socket, vk, index):
       # Events:
       # 1. Skip sub_block

   def get_my_index(self):
      for index, vk in enumerate(VKBook.get_delegates()):
          if vk == self.verifying_key:
              return index

   def send_make_block(self, block_num):

   async def recv_sb_merkle_sig(self):
       # need to keep in an array based on sbb_index.
       # need to resolve differences across sub-blocks in the same order
       # once the sub-tree that it is responsible for is resolved, then send its MS to master nodes and other delegates

   async def recv_sb_merkle_sigs_from_other_delegates(self):
       # perhaps can be combined with the above,
       # verify with its copy and matches, then send the vote to masters
       # only need to keep this until its own sub-tree is ready

