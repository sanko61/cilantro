from unittest import TestCase, main
import zmq, zmq.asyncio, asyncio, time
from multiprocessing import Process

async def _client(s, tm=3):
    s.connect('tcp://localhost:4321')
    print('Client: waiting for messages...')
    msg_count = 0
    while True:
        msg = await s.recv_multipart()
        print('Client: <Recieved>', msg)
        msg_count += 1
        if msg_count >= tm:
            s.close()
            return

def client(delay=0, total_msgs=5):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b'topic')
    print('Server <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(_client(socket, total_msgs))

async def _server(s, tm):
    s.bind('tcp://*:4321')
    await asyncio.sleep(0.5)
    msg_count = 0
    while True:
        print('Server: sending msg...')
        s.send_multipart([b'topic', 'ready {}...'.format(msg_count).encode()])
        msg_count += 1
        await asyncio.sleep(1)
        if msg_count >= tm:
            s.close()
            return

def server(delay=0, total_msgs=3):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PUB)
    print('Client <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(_server(socket, total_msgs))

class TestLoopBehavior(TestCase):

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b'topic')

    def setUp(self):
        print('\n' + '#' * 64 + '\n')
        print(self.id())
        print('\n' + '#' * 64 + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        cls.loop.close()

    def test_concurrent_loop_2_procs(self):
        proc2 = Process(target=server, args=(3,))
        proc1 = Process(target=client, args=())
        proc1.start()
        proc2.start()
        time.sleep(10)
        proc1.terminate()
        proc2.terminate()

    def test_concurrent_loop_local_and_1_proc(self):
        proc2 = Process(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(_client(self.socket, ))

if __name__ == '__main__':
    main()
