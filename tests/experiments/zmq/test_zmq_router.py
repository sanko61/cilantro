from unittest import TestCase, main
import zmq, zmq.asyncio, asyncio

async def server(socket, delay=0, total_msgs=3):
    await asyncio.sleep(delay)
    socket.bind('tcp://*:4321')
    print('Server: waiting for messages...')
    msg_count = 0
    while True:
        msg = await socket.recv_multipart()
        if msg[1] == b'':
            print('Server: connection from', msg[0])
            socket.send_multipart(msg)
        else:
            print('Server: <Recieved>', msg)
            msg_count += 1
            if msg_count >= total_msgs:
                return

async def client_probe(socket, delay=0, total_msgs=3):
    await asyncio.sleep(delay)
    socket.connect('tcp://localhost:4321')
    print('Client: Waiting for connection')
    msg = await socket.recv_multipart()
    print('Client: connected to', msg[0])
    msg_count = 0
    while True:
        print('Client: sending msg...')
        socket.send_multipart([msg[0], 'ready {}...'.format(msg_count).encode()])
        msg_count += 1
        await asyncio.sleep(1)
        if msg_count >= total_msgs:
            socket.close()
            return

async def client(socket, delay=0, total_msgs=10):
    await asyncio.sleep(delay)
    socket.connect('tcp://localhost:4321')
    print('Client: supposed to be connected to b\'node_1\'')
    msg_count = 0
    while True:
        print('Client: sending msg...')
        socket.send_multipart([b'node_1', 'ready {}...'.format(msg_count).encode()])
        msg_count += 1
        await asyncio.sleep(1)
        if msg_count >= total_msgs:
            return

class TestLSocketBase(TestCase):

    loop = asyncio.get_event_loop()

    def setUp(self):
        print('\n' + '#' * 64 + '\n')
        print(self.id())
        print('\n' + '#' * 64 + '\n')
        self.ctx = zmq.asyncio.Context()
        self.s1 = self.ctx.socket(zmq.ROUTER)
        self.s1.identity = b'node_1'
        self.s2 = self.ctx.socket(zmq.ROUTER)
        self.s2.identity = b'node_2'

    def tearDown(self):
        self.s1.close()
        self.s2.close()

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        cls.loop.close()

    def test_router_probe_connect_first(self):
        self.s2.probe_router = 1
        self.loop.run_until_complete(asyncio.gather(
            server(self.s1, 3), client_probe(self.s2)
        ))

    def test_router_no_probe_connect_first(self):
        self.loop.run_until_complete(asyncio.gather(
            server(self.s1, 3), client(self.s2)
        ))


if __name__ == '__main__':
    main()
