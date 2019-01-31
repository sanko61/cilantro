from unittest import TestCase, main
import zmq, zmq.asyncio, asyncio

async def client(socket, delay=0, total_msgs=3):
    print('Client: starting in {}s...'.format(delay))
    await asyncio.sleep(delay)
    socket.connect('tcp://localhost:4321')
    print('Client: waiting for messages...')
    msg_count = 0
    while True:
        msg = await socket.recv_multipart()
        print('Client: <Recieved>', msg)
        msg_count += 1
        if msg_count >= total_msgs:
            return

async def server(socket, delay=0, total_msgs=5):
    print('Server: starting in {}s...'.format(delay))
    await asyncio.sleep(delay)
    socket.bind('tcp://*:4321')
    await asyncio.sleep(0.1)
    msg_count = 0
    while True:
        print('Server: sending msg...')
        socket.send_multipart([b'topic', 'ready {}...'.format(msg_count).encode()])
        msg_count += 1
        await asyncio.sleep(1)
        if msg_count >= total_msgs:
            return

class TestZMQPubSub(TestCase):

    loop = asyncio.get_event_loop()

    def setUp(self):
        print('\n' + '#' * 64 + '\n')
        print(self.id())
        print('\n' + '#' * 64 + '\n')
        self.ctx = zmq.asyncio.Context()
        self.s1 = self.ctx.socket(zmq.PUB)
        self.s2 = self.ctx.socket(zmq.SUB)
        self.s2.setsockopt(zmq.SUBSCRIBE, b'topic')

    def tearDown(self):
        self.s1.close()
        self.s2.close()

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        cls.loop.close()

    def test_pubsub_late_bind(self):
        self.loop.run_until_complete(asyncio.gather(
            server(self.s1, 3), client(self.s2)
        ))


if __name__ == '__main__':
    main()
