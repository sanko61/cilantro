from unittest import TestCase, main
import zmq, zmq.asyncio, asyncio, time, traceback, sys, os
from multiprocessing import Process

async def _client(s, tm=3, raise_e=False, fail=False, async_loop=False):
    if async_loop:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    s.connect('tcp://localhost:4321')
    print('Client: waiting for messages...')
    msg_count = 0
    while True:
        msg = await s.recv_multipart()
        print('Client: <Recieved>', msg)
        if raise_e:
            try:
                raise Exception('Woah')
            except Exception as e:
                print('Error: Got an exception {}!'.format(e))
        elif fail:
            1 / 0
        msg_count += 1
        if msg_count >= tm:
            s.close()
            return

async def _runner(custom_msg=None):
    while True:
        if custom_msg:
            print(custom_msg)
        else:
            print('I am still running')
        await asyncio.sleep(1)

def client(delay=0, total_msgs=5, raise_e=False, fail=False, async_loop=None):
    if async_loop:
        loop = async_loop
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b'topic')
    print('Server <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(_client(socket, total_msgs, raise_e, fail))

async def _server(s, tm, raise_e=False, fail=False):
    s.bind('tcp://*:4321')
    await asyncio.sleep(0.5)
    msg_count = 0
    while True:
        if raise_e:
            try:
                raise Exception('Woah')
            except Exception as e:
                print('Error: Got an exception {}!'.format(e))
            finally:
                print('finally')
        elif fail:
            1 / 0
        print('Server: sending msg...')
        s.send_multipart([b'topic', 'ready {}...'.format(msg_count).encode()])
        msg_count += 1
        await asyncio.sleep(1)
        if msg_count >= tm:
            s.close()
            return

def server(delay=0, total_msgs=3, raise_e=False, fail=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PUB)
    print('Client <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(_server(socket, total_msgs, raise_e, fail))

def gather_server(delay=0, total_msgs=3, raise_e=False, fail=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PUB)
    print('Client <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(asyncio.gather(
        _server(socket, total_msgs, raise_e, fail),
        _runner('loop with server')
    ))

def server_with_client(delay=0, total_msgs=3, raise_e=False, fail=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b'topic')
    proc = LProcess(target=gather_server, args=(3,), kwargs={'fail': False})
    proc.start()
    print('Client <{}>: starting in {}s...'.format(id(loop), delay))
    time.sleep(delay)
    loop.run_until_complete(asyncio.gather(
        _client(socket, total_msgs, fail=True)
    ))

def top_level_process():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server_with_client()

class LoggerWriter:
    def __init__(self, level):
        self.level = level
    def write(self, message):
        if message != '\n':
            self.level(message)
    def flush(self):
        return

class LProcess(Process):
    def run(self):
        try:
            super().run()
        except Exception as e:
            err_msg = '\nLProcess::: Exception caught on ' + self.name + ':\n' + str(e)
            err_msg += '\n' + traceback.format_exc()
            print(err_msg)
        finally:
            print("<--- {} Terminating <---".format(self.name))
            # TODO -- signal to parent to call .join() on this process and clean up nicely

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

    def test_concurrent_loop_local_and_1_proc_with_caught_exception(self):
        proc2 = Process(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(_client(self.socket, raise_e=True))

    def test_concurrent_loop_local_and_1_proc_with_uncaught_exception(self):
        proc2 = Process(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(_client(self.socket, fail=True))

    def test_concurrent_loop_local_and_1_proc_with_caught_exception_in_gather(self):
        proc2 = Process(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(asyncio.gather(
            _client(self.socket, raise_e=True),
            _runner()
        ))

    def test_concurrent_loop_local_and_1_proc_with_uncaught_exception_in_gather(self):
        proc2 = Process(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(asyncio.gather(
            _client(self.socket, fail=True),
            _runner(),
            # return_exceptions=True
        ))
        print('Loop did not die: {}'.format(self.loop.is_running()))

    def test_concurrent_loop_local_and_1_proc_with_uncaught_exception_in_gather_catching_outside_proc(self):
        proc2 = LProcess(target=server, args=(3,))
        proc2.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(asyncio.gather(
            _client(self.socket, fail=True),
            _runner(),
            # return_exceptions=True
        ))
        print('Loop did not die: {}'.format(self.loop.is_running()))

    def test_concurrent_loop_local_and_1_proc_with_uncaught_exception_in_gather_inside_server_catching_outside_proc(self):
        proc1 = LProcess(target=gather_server, args=(3, ), kwargs={'fail': True})
        proc1.start()
        delay = 0
        print('Client <{}>: starting in {}s...'.format(id(self.loop), delay))
        time.sleep(delay)
        self.loop.run_until_complete(asyncio.gather(
            _client(self.socket),
            # _runner(),
            # return_exceptions=True
        ))
        print('Loop did not die: {}'.format(self.loop.is_running()))

    def test_concurrent_loop_3_layer(self):
        proc1 = LProcess(target=top_level_process)
        proc1.start()

if __name__ == '__main__':
    main()
