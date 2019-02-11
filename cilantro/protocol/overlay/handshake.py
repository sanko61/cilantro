import zmq, zmq.asyncio, asyncio, traceback, time
from os import getenv as env
from cilantro.constants.overlay_network import *
from cilantro.constants.ports import AUTH_PORT
from zmq.auth.thread import ThreadAuthenticator
from zmq.auth.asyncio import AsyncioAuthenticator
from cilantro.protocol.overlay.event import Event
from cilantro.protocol.overlay.ip import *
from cilantro.protocol.comm.socket_auth import SocketAuth
from cilantro.utils.keys import Keys
from cilantro.logger import get_logger
from cilantro.storage.vkbook import VKBook
from collections import defaultdict

class Handshake:
    log = get_logger('Handshake')
    host_ip = HOST_IP
    port = AUTH_PORT
    url = 'tcp://*:{}'.format(port)
    pepper = PEPPER.encode()
    authorized_nodes = defaultdict(dict)
    authorized_nodes['*'] = {}
    unknown_authorized_nodes = {}
    is_setup = False

    def __init__(self, loop=None, ctx=None):
        if not self.is_setup:
            self.loop = loop or asyncio.get_event_loop()
            self.ctx = ctx or zmq.asyncio.Context()
            self.identity = '{}:{}'.format(self.host_ip, Keys.vk)
            self.auth = AsyncioAuthenticator(context=self.ctx, loop=self.loop)
            self.auth.configure_curve(domain="*", location=zmq.auth.CURVE_ALLOW_ANY)
            self.auth.start()

            self.server_sock = self.ctx.socket(zmq.ROUTER)
            self.server_sock.setsockopt(zmq.ROUTER_MANDATORY, 1)  # FOR DEBUG ONLY
            self.server_sock.setsockopt(zmq.ROUTER_HANDOVER, 1)
            self.server_sock.curve_secretkey = Keys.private_key
            self.server_sock.curve_publickey = Keys.public_key
            self.server_sock.curve_server = True
            self.server_sock.bind(self.url)
            self.is_setup = True
            self.count = 0

    async def initiate_handshake(self, ip, vk, domain='*'):
        if ip == self.host_ip and vk == Keys.vk:
        # raghu - why do we need this self authorization?
            self.authorized_nodes[domain][vk] = ip
            Event.emit({'event': 'authorized', 'vk': vk, 'ip': ip, 'domain': domain})
            return True
        elif self.check_previously_authorized(ip, vk, domain):
            return True
        else:
            start = time.time()
            authorized = False
            url = 'tcp://{}:{}'.format(ip, self.port)
            self.log.info('Sending handshake request from {} to {} (vk={})'.format(self.host_ip, ip, vk))
            client_sock = self.ctx.socket(zmq.DEALER)
            client_sock.setsockopt(zmq.IDENTITY, '{}:{}'.format(self.identity, self.count).encode())
            client_sock.curve_secretkey = Keys.private_key
            client_sock.curve_publickey = Keys.public_key
            client_sock.curve_serverkey = Keys.vk2pk(vk)
            client_sock.connect(url)
            client_sock.send_multipart([domain.encode()])
            self.count += 1

            try:
                domain = [chunk.decode() for chunk in await asyncio.wait_for(client_sock.recv_multipart(), AUTH_TIMEOUT)][0]
                self.log.info('Received a handshake reply from {} to {} (vk={})'.format(ip, self.host_ip, vk))
                authorized = self.process_handshake(ip, vk, domain)
                self.log.notice('Complete (took {}s): {} <=o= {} (vk={})'.format(time.time()-start, self.host_ip, ip, vk))
            except asyncio.TimeoutError:
                if self.check_previously_authorized(ip, vk, domain):
                    authorized = True
                    self.log.notice('Complete2 (took {}s): {} <=o= {} (vk={})'.format(time.time()-start, self.host_ip, ip, vk))
                else:
                    self.log.warning('Timeout (took {}s): {} <=:= {} (vk={})'.format(time.time()-start, self.host_ip, ip, vk))
                    self.log.warning('Authorized nodes: {}'.format(self.authorized_nodes[domain]))
            except Exception:
                self.log.error(traceback.format_exc())
            finally:
                client_sock.close()

            return authorized

    async def listen(self):
        self.log.info('Listening to other nodes on {}'.format(self.url))
        while True:
            try:
                ip_vk, domain = [chunk.decode() for chunk in await self.server_sock.recv_multipart()]
                ip, vk, ct = ip_vk.split(':')
                self.log.info('Received a handshake request from {} to {} (vk={})'.format(ip, self.host_ip, vk))
                authorized = self.process_handshake(ip, vk, domain)
                if authorized:
                    self.server_sock.send_multipart([ip_vk.encode(), domain.encode()])
            except Exception as e:
                self.log.error(traceback.format_exc())

    def process_handshake(self, ip, vk, domain):
        if self.check_previously_authorized(ip, vk, domain):
            return True
        else:
            if self.validate_roles_with_domain(domain, vk):
                self.authorized_nodes[domain][vk] = ip
                self.authorized_nodes['*'][vk] = ip
                self.log.info('Authorized: {} <=O= {} (vk={}, domain={})'.format(self.host_ip, ip, vk, domain))
                Event.emit({'event': 'authorized', 'vk': vk, 'ip': ip, 'domain': domain})
                return True
            else:
                self.unknown_authorized_nodes[vk] = ip
                # NOTE The sender proved that it has the VK via the router's identity frame but the sender is not found in the receiver's VKBook
                self.log.warning('Unauthroized VK: {} <=X= {} (vk={}, domain={}), saving to unknown_authorized_nodes for now'.format(self.host_ip, ip, vk, domain))
                Event.emit({'event': 'unauthorized_ip', 'vk': vk, 'ip': ip, 'domain': domain})
                return False

    def check_previously_authorized(self, ip, vk, domain):
        if not self.authorized_nodes.get(domain):
            self.authorized_nodes[domain] = {}
        if self.authorized_nodes[domain].get(vk):
            self.log.spam('Previously Authorized: {} <=O= {} (vk={}, domain={})'.format(self.host_ip, ip, vk, domain))
            return True
        elif self.authorized_nodes['*'].get(vk):
            if ip == self.authorized_nodes['*'][vk]:
                self.log.info('Already Authorized To Domain: {} <=O= {} (vk={}, domain={})'.format(self.host_ip, ip, vk, domain))
                self.authorized_nodes[domain][vk] = ip
                return True
        elif self.unknown_authorized_nodes.get(vk):
            if ip == self.unknown_authorized_nodes[vk]:
                self.log.info('Found and authorized previously unknown but authorized node: {} <=O= {} (vk={}, domain={})'.format(self.host_ip, ip, vk, domain))
                self.authorized_nodes['*'][vk] = ip
                self.authorized_nodes[domain][vk] = ip
            else:
                self.log.info('Removing stale unknown VK: {} =||= {} (vk={})'.format(self.host_ip, ip, vk))
                del self.unknown_authorized_nodes[vk]
            return False
        return False

    @staticmethod
    def validate_roles_with_domain(domain, vk, roles='any'):
        if roles == 'any':
            return vk in VKBook.get_all()
        else:
            if 'masternodes' in roles and vk in VKBook.get_masternodes():
                return True
            if 'witnesses' in roles and vk in VKBook.get_witnesses():
                return True
            if 'delegates' in roles and vk in VKBook.get_delegates():
                return True
        return False
