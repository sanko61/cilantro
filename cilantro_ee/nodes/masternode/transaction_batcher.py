from cilantro_ee.crypto import Wallet

from cilantro_ee.messages.message import Message
from cilantro_ee.messages.message_type import MessageType

import hashlib
import time


class TransactionBatcher:
    def __init__(self, wallet: Wallet, queue):
        self.wallet = wallet
        self.queue = queue

    def pack_current_queue(self, tx_number=100):
        # Pop elements off into a list
        tx_list = []
        while len(tx_list) < tx_number or len(self.queue) > 0:
            tx_list.append(self.queue.pop(0))

        # Hash transactions to come up with the entire hash of the batch
        h = hashlib.sha3_256()
        for tx in tx_list:
            tx_bytes = tx.as_builder().to_bytes_packed()
            h.update(tx_bytes)

        # Add a timestamp
        timestamp = time.time()
        h.update('{}'.format(timestamp).encode())
        input_hash = h.digest()

        # Sign the message for verification
        signature = self.wallet.sign(input_hash)

        msg = Message.get_signed_message_packed_2(
            wallet=self.wallet,
            msg_type=MessageType.TRANSACTION_BATCH,
            transactions=[t for t in tx_list],
            timestamp=timestamp,
            signature=signature,
            inputHash=input_hash,
            sender=self.wallet.verifying_key()
        )

        return msg
