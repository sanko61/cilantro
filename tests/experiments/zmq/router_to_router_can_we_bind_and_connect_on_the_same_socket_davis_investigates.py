import zmq.asyncio
import asyncio
from cilantro.logger import get_logger
import time
from multiprocessing import Process
import random


async def listen(sock, log):
    log.socket("Starting listening...")
    while True:
        log.info("Waiting for msg...")
        msg = await sock.recv_multipart()
        log.notice("GOT MSG {}!".format(msg))


async def talk(sock, log, msg, receiver_ids):
    log.socket("bout to start talking with msg {}".format(msg.decode()))
    while True:
        sleep = random.randint(0, 4)
        log.debug("sleeping for {} seconds before sending message".format(sleep))
        await asyncio.sleep(sleep)
        for id in receiver_ids:  # TODO take a random sample from receiver_ids?
            log.debugv("sending to id {}".format(id.decode()))
            sock.send_multipart([id, msg])


def build_comm(identity: bytes):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(socket_type=zmq.ROUTER)
    sock.setsockopt(zmq.IDENTITY, identity)
    return loop, ctx, sock


def start_node(identity, url, external_urls, external_ids):
    log = get_logger("Node[{}]".format(identity.decode()))
    loop, ctx, sock = build_comm(identity=identity)
    log.debug("BINDing to url {}".format(url))
    msg = b'hi its me -- ' + identity
    sock.bind(url)

    for url in external_urls:
        log.debug("CONNECTing to url {}".format(url))
        sock.connect(url)

    loop.run_until_complete(asyncio.gather(listen(sock, log), talk(sock, log, msg, external_ids)))


if __name__ == '__main__':
    ID1, ID2, ID3, ID4, ID5 = b'1', b'2', b'3', b'4', b'5'
    URL1 = "tcp://127.0.0.1:9001"
    URL2 = "tcp://127.0.0.1:9002"
    URL3 = "tcp://127.0.0.1:9003"
    URL4 = "tcp://127.0.0.1:9004"
    URL5 = "tcp://127.0.0.1:9005"
    ALL_IDS = [ID1, ID2, ID3, ID4, ID5]
    ALL_URLS = [URL1, URL2, URL3, URL4, URL5]

    node1 = Process(target=start_node, args=(ID1, URL1, ALL_URLS, ALL_IDS))
    node2 = Process(target=start_node, args=(ID2, URL2, ALL_URLS, ALL_IDS))
    node3 = Process(target=start_node, args=(ID3, URL3, ALL_URLS, ALL_IDS))

    for p in (node1, node2, node3):
        p.start()

