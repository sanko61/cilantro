from unittest import TestCase, main
import zmq, zmq.asyncio, asyncio

async def client(d1, d2):
    url = 'tcp://localhost:9413'
    print('Dealer 1: Sending msg...')
    d1.connect(url)
    d1.send_multipart([b'I am dealer 1'])
    await asyncio.sleep(3)
    print('Dealer 2: Sending msg...')
    d2.connect(url)
    d2.send_multipart([b'I am dealer 2'])

async def server(socket, delay=0, total_msgs=2):
    print('Server: starting in {}s...'.format(delay))
    await asyncio.sleep(delay)
    socket.bind('tcp://*:9413')
    await asyncio.sleep(0.1)
    print('Server: receiving msg...')
    msg_count = 0
    while True:
        msg = await socket.recv_multipart()
        print('Server: received msg {}'.format(msg))
        msg_count += 1
        if msg_count == total_msgs:
            break

class TestZMQPubSub(TestCase):

    loop = asyncio.get_event_loop()

    def setUp(self):
        print('\n' + '#' * 64 + '\n')
        print(self.id())
        print('\n' + '#' * 64 + '\n')
        self.ctx = zmq.asyncio.Context()
        self.identity = b'dealer'
        self.d1 = self.ctx.socket(zmq.DEALER)
        self.d1.setsockopt(zmq.IDENTITY, self.identity)
        self.d2 = self.ctx.socket(zmq.DEALER)
        self.d2.setsockopt(zmq.IDENTITY, self.identity)
        self.rt = self.ctx.socket(zmq.ROUTER)
        self.rt.setsockopt(zmq.ROUTER_HANDOVER, 1)

    def tearDown(self):
        self.d1.close()
        self.d2.close()
        self.rt.close()

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        cls.loop.close()

    def test_dealer_connect_same_identity_on_two_sockets(self):
        self.loop.run_until_complete(asyncio.gather(
            server(self.rt), client(self.d1, self.d2)
        ))


if __name__ == '__main__':
    main()
