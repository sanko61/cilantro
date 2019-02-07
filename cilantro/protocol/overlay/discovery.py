import zmq, zmq.asyncio, asyncio, traceback
from os import getenv as env
from cilantro.constants.overlay_network import *
from cilantro.constants.ports import DISCOVERY_PORT
from cilantro.protocol.overlay.ip import *
from cilantro.logger import get_logger
from cilantro.storage.vkbook import VKBook
from cilantro.constants.ports import DHT_PORT
from cilantro.protocol.overlay.kademlia.utils import digest
from cilantro.protocol.overlay.kademlia.node import Node


class Discovery:

    def __init__(self, vk, zmq_ctx):
        self.log = get_logger('Overlay.Server.Discovery')
        self.vk  = vk
        self.ctx = zmq_ctx
        self.host_ip = HOST_IP
        # these part of genesis scripts?
        self.port = DISCOVERY_PORT
        self.pepper = PEPPER.encode()

        self.url = 'tcp://*:{}'.format(self.port)
        self.sock = self.ctx.socket(zmq.ROUTER)
        self.sock.setsockopt(zmq.IDENTITY, self.host_ip.encode())
        self.sock.setsockopt(zmq.ROUTER_HANDOVER, 1)
        self.sock.setsockopt(zmq.LINGER, 3)
        self.sock.bind(self.url)

        self.discovered_nodes = {}
        self.connections = {}
        self.is_connected = False
        self.is_masternode = False
        self.is_listen_ready = False
        if VKBook.is_node_type('masternode', self.vk):
            self.is_masternode = True
            self.is_listen_ready = True

    async def listen(self):
        self.log.debug('Listening to other nodes on {}'.format(self.url))
        while True:
            try:
                msg = await self.sock.recv_multipart()
                self.log.spam("Got msg over discovery socket: {}".format(msg))
                ip, pepper = msg[:2]

                if pepper != self.pepper:
                    self.log.warning("Node with ip {} tried to connect using incorrect pepper {}!".format(ip, pepper))
                    continue

                if len(msg) == 2:
                    self.reply(ip)

                elif len(msg) == 3:
                    vk = msg[-1]
                    self.discovered_nodes[vk.decode()] = ip.decode()
                    self.is_listen_ready = True

            except Exception as e:
                self.log.error(traceback.format_exc())

        self.sock.close()
        self.log.fatal('Discovery DIED')

    def request(self, ip):
        self.sock.send_multipart([ip, self.pepper])

    def reply(self, ip):
        if self.is_listen_ready and ip != self.host_ip:
            self.sock.send_multipart([ip, self.pepper, self.vk.encode()])
            self.is_connected = True

    def connect(self, ips):
        self.log.spam("Attempting to connect to IP range {}".format(ips[0]))
        for ip in ips:
            if ip == self.host_ip:
                continue
            url = 'tcp://{}:{}'.format(ip, self.port)
            if not self.connections.get(ip):
                self.sock.connect(url)
                self.connections[ip] = url
            self.request(ip.encode())

    # need to test if this creates additional issues of listening after we disconect
    def disconnect(self):
        self.log.spam("Attempting to disconnect discovery connections")
        for url in self.connections.itervalues():
            self.sock.disconnect(url)


    async def discover_nodes(self, start_ip):
        self.log.info('We have the following boot nodes: {}'.format(VKBook.bootnodes))

        # no need to discover anyone if it is the solo masternode in the network
        if (self.is_masternode and len(VKBook.get_masternodes()) == 1):
            self.log.important('Bootstrapping as the only masternode.')
            return True

        try_count = 0
        while True:
            if len(VKBook.bootnodes) > 0: # TODO refine logic post-anarchy-net
                self.log.info('Connecting to boot nodes: {}'.format(VKBook.bootnodes))
                self.connect(VKBook.bootnodes)
            else:
                ip_range = start_ip if type(start_ip) == list else get_ip_range(start_ip)
                self.log.info('Connecting to this ip-range: {} to {}'.format(ip_range[0], ip_range[-1]))
                self.connect(ip_range)
            try_count += 1
            if (self.is_masternode and len(self.discovered_nodes) == 0 and try_count >= RETRIES_BEFORE_SOLO_BOOT):
                self.log.important('Bootstrapping as the only masternode so far.')
                return True
            elif len(self.discovered_nodes) >= MIN_BOOTSTRAP_NODES:
                self.log.info('Found {} nodes to bootstrap: {}'.format(
                    len(self.discovered_nodes), self.discovered_nodes
                ))
                return True
            elif try_count >= DISCOVERY_RETRIES:
                self.log.info('Did not find enough nodes after {} tries ({}/{}).'.format(
                    try_count,
                    len(self.discovered_nodes),
                    MIN_BOOTSTRAP_NODES
                ))
                return False

            await asyncio.sleep(DISCOVERY_TIMEOUT)

    async def discover_and_connect(self):
        if not await self.discover_nodes(self.host_ip):
            self.log.critical('''
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
x   DISCOVERY FAILED: Cannot find enough nodes ({}/{}) and not a masternode
x       Retrying...
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            '''.format(len(self.discovered_nodes), MIN_BOOTSTRAP_NODES))
            raise Exception('Failed to discover any nodes. Killing myself with shame!')
        self.log.success('''
###########################################################################
#   DISCOVERY COMPLETE
###########################################################################\
        ''')
        self.is_listen_ready = True
        # raghu - todo - change interface of nodes. No need to create node list and import DHT_PORT etc here
        if len(self.discovered_nodes) > 0:
            addrs = [Node(digest(vk), ip=self.discovered_nodes[vk], port=DHT_PORT, vk=vk) \
                for vk in self.discovered_nodes if vk is not self.vk]
            return addrs
            await self.network.bootstrap(addrs)
        return []

