import unittest, time, asyncio
import zmq, zmq.asyncio, traceback
from unittest import TestCase
from os import listdir, makedirs
from os.path import exists, join
from nacl.bindings import crypto_sign_ed25519_sk_to_curve25519
from cilantro.utils.lprocess import LProcess
from cilantro.constants.testnet import TESTNET_MASTERNODES, TESTNET_WITNESSES, TESTNET_DELEGATES

class Node:
    def __init__(self, iter: int, port: int):
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        self.ctx = zmq.asyncio.Context()
        self.iter = iter
        self.sock = self.ctx.socket(zmq.ROUTER)
        self.sock.setsockopt(zmq.IDENTITY, "server_router".encode())
        self.sock.setsockopt(zmq.LINGER, 10 ) 
        self.port = port
        self.host = "localhost"
        self.protocol = "tcp"
        self.ip = "tcp://localhost:{}".format(port)
        self.lip = "tcp://*:{}".format(port)

        # self.run()

    # def run(self):
        # self.loop.run_until_complete(asyncio.gather(self.handle_task()))

    async def handle_task(self):
        # print("running task at node")
        while self.iter > 0:
            start = time.time()
            # print("receiving at node")
            msg1 = await self.sock.recv_multipart()
            # print(msg1)
            addr = msg1[0]
            data = msg1[1]
            self.sock.send_multipart([addr, data])
            self.iter = self.iter - 1
            time.sleep(1)

    async def run_task(self):
        # print("running node")
        results = await asyncio.gather(self.handle_task())
        return results


class OtherNode:
    def __init__(self, index: int, identity: str, ip: str):
        self.index = index
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.setsockopt(zmq.LINGER, 10 ) 
        # self.sock.setsockopt(zmq.IDENTITY, identity.encode())
        self.ip = ip
        self.tasks = []
        self.tasks.append(self.handle_task())

        self.run()

    async def run_tasks(self):
        # print("running other node")
        results = await asyncio.gather(*self.tasks)
        return results

    def run(self):
        self.loop.run_until_complete(self.run_tasks())

    async def handle_task(self):
        self.sock.connect(self.ip)
        await asyncio.sleep(1)
        msg = b'\x02'
        self.sock.send_multipart([msg])
        # print("sent message to node")
        msg1 = await self.sock.recv_multipart()
        # print("received message from node")
        



class TestRouter(TestCase):

    def test_setup(self):
        loop = asyncio.get_event_loop()
        node = Node(1, 4320)
        node.sock.bind(node.lip)
        # print("initialized node")

        self.other_node = LProcess(target=OtherNode, name="other_node", 
                                   kwargs={"index": 0, "identity": "client", "ip": node.ip})
        self.other_node.start()

        # print("started other node")

        # time.sleep(1)
        # self.sock.bind(port=self.port, ip=self.host, protocol=self.protocol)

        # await node.handle_task()
        loop.run_until_complete(node.run_task())
        # print("done with my job")
        node.sock.close()
        time.sleep(1)
        # await self.listen(self.sock, 1)
        # start = time.time()
        # msg1 = await self.sock.recv_multipart()
        # addr = msg1[0]
        # data = msg1[1]
        # self.sock.send_multipart([addr, data])
        # msg2 = await sock.recv_multipart()

    def test_two_dealers(self):
        loop = asyncio.get_event_loop()
        node = Node(2, 4321)
        node.sock.bind(node.lip)
        # print("initialized node")

        other_node = LProcess(target=OtherNode, name="other_node_0", 
                                   kwargs={"index": 0, "identity": "client", "ip": node.ip})
        other_node.start()

        other_node2 = LProcess(target=OtherNode, name="other_node_1", 
                                   kwargs={"index": 1, "identity": "client", "ip": node.ip})
        other_node2.start()
        # print("started other node")

        loop.run_until_complete(node.run_task())
        # print("done with my job")
        time.sleep(1)
        node.sock.close()

        # await node.handle_task()
        # self.sock.bind(port=self.port, ip=self.host, protocol=self.protocol)

        # loop.run_until_complete(asyncio.gather(node.handle_task()))
        # await self.listen(self.sock)
        # start = time.time()
        # msg1 = await self.sock.recv_multipart()
        # addr = msg1[0]
        # data = msg1[1]
        # self.sock.send_multipart([addr, data])
        # msg2 = await sock.recv_multipart()
        # log = "{} after {} secs".format(os.getenv('HOST_NAME'), time.time() - start)

if __name__ == '__main__':
    unittest.main()
