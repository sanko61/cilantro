from cilantro.protocol.comm.lsocket import LSocketBase
from cilantro.messages.envelope.envelope import Envelope
import time, asyncio
from collections import defaultdict, deque
from typing import List

# How long a Router socket will wait for a PONG after sending a PING. Should be a n^2 - 1 b/c of exponential delays
# between retries (i.e. we retry in 1, then 2, then 4, then 8 seconds and so on)
PING_TIMEOUT = 127

# How long before a 'session' with another Router client expires. After the session expires, a new PING/PONG exchange
# must occur before any messages can be sent to that client
SESSION_TIMEOUT = 1800  # 30 minutes

PING, PONG = b'PING', b'PONG'


class LSocketRouter(LSocketBase):

    def __init__(self, *args, ipc=False, **kwargs):
        super().__init__(*args, **kwargs)

        # For all 3 of below data structures, the keys are the Router socket ID of a client
        self.recent_pongs = {}  # Tracks last times a PONG was received for each client. Val is epoch time (int)
        self.deferred_msgs = defaultdict(deque)  # Messages that are awaiting a PONG before sent
        self.ready_sockets = defaultdict(bool)
        if not ipc:
            self.socket.probe_router = 1

    def send_envelope(self, env: Envelope, header: bytes=None):
        assert header is not None, "Header must be identity frame when using send on Router sockets. Cannot be None."

        if not self.ready_sockets.get(header):
            self.log.debugv("Deferring msg to client with ID {} since we have not had recent contract".format(header))
            self.deferred_msgs[header].append(env.serialize())
        else:
            self.socket.send_multipart([header, env.serialize()])

    def _handle_node_online(self, event: dict):
        super()._handle_node_online(event)
        self.ready_sockets[event['vk'].encode()] = False

    def _process_msg(self, msg: List[bytes]) -> bool:

        if len(msg) == 2 and msg[1] == b'':
            self.ready_sockets[msg[0]] = True
            self.log.important("Received a connect request from {}".format(msg[0]))
            self.socket.send_multipart([msg[0], b'ack_connect'])
            self._mark_client_as_online(msg[0])
            return False
        elif len(msg) == 2 and msg[1] == b'ack_connect':
            self._mark_client_as_online(msg[0])
            return False
        else:
            self.log.spam("Router RECEIVED msg {}".format(msg))
            return True

        # If message length is not 2, we assume its an IPC msg, and return True.
        # TODO -- more robust logic here. Can we maybe set a flag on the sock indicating its an IPC socket?
        if len(msg) != 2:
            return True

    def _mark_client_as_online(self, client_id: bytes):
        self.log.spam("Marking client with ID {} as online".format(client_id))

        # Send out any queued msgs
        if client_id in self.deferred_msgs:
            self.log.debugv("Flushing {} deferred messages from client with ID {}"
                            .format(len(self.deferred_msgs[client_id]), client_id))
            for _ in range(len(self.deferred_msgs[client_id])):
                env_binary = self.deferred_msgs[client_id].popleft()
                assert type(env_binary) is bytes, "Expected deferred_msgs deque to be bytes, not {}".format(env_binary)
                self.socket.send_multipart([client_id, env_binary])
            del self.deferred_msgs[client_id]
