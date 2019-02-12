from cilantro.messages.base.base import MessageBase
from cilantro.messages.utils import validate_hex
import json, time
from cilantro.protocol import wallet
from cilantro.utils.keys import Keys

class MerkleSignature(MessageBase):
    """
    TODO -- switch this class to use capnp
    """

    SIG = 'signature'
    TS = 'timestamp'
    SENDER = 'sender'

    def __eq__(self, other_ms):
        """Check two merkle signatures have identical features"""
        return self._data == other_ms._data

    def validate(self):
        assert type(self._data) == dict, "_data is not a dictionary"
        assert self.SIG in self._data, "Signature field missing from _data: {}".format(self._data)
        assert self.TS in self._data, "Timestamp field missing from _data: {}".format(self._data)
        assert self.SENDER in self._data, "Sender field missing from _data: {}".format(self._data)

        validate_hex(self._data[self.SIG], 128, self.SIG)
        validate_hex(self._data[self.SENDER], 64, self.SENDER)
        # TODO Validate timestamp somehow?

    def serialize(self):
        return json.dumps(self._data).encode()

    def verify(self, msg):
        verifying_key = self.sender

        if validate_hex(verifying_key, length=64, raise_err=False):
            return wallet.verify(verifying_key, msg, self.signature)
        else:
            return False

    @classmethod
    def create(cls, sig_hex: str, sender: str, timestamp: str=None, validate=True):
        timestamp = timestamp or str(time.time())
        data = {cls.SIG: sig_hex, cls.TS: timestamp, cls.SENDER: sender}
        return cls.from_data(data, validate=validate)

    @classmethod
    def create_from_payload(cls, payload: bytes, verifying_key: str=None, timestamp: str=None):
        sig_hex = wallet.sign(Keys.sk, payload)
        return cls.create(sig_hex=sig_hex, sender=Keys.vk)

    @classmethod
    def _deserialize_data(cls, data: bytes):
        return json.loads(data.decode())

    @property
    def signature(self) -> str:
        """
        The cryptographic signature, represented as 128 character hex string.
        """
        return self._data[self.SIG]

    @property
    def timestamp(self) -> str:
        """
        The time the signature was created, currently stored as an unix epoch string.
        """
        return self._data[self.TS]

    @property
    def sender(self) -> str:
        """
        The verifying key of the signer, represented as a 64 character hex string
        """
        return self._data[self.SENDER]


def build_test_merkle_sig(msg: bytes=b'some default payload', sk=None, vk=None) -> MerkleSignature:
    """
    Builds a 'test' merkle signature. Used exclusively for unit tests
    :return:
    """
    import time

    signature = wallet.sign(Keys.sk, msg)

    return MerkleSignature.create(sig_hex=signature, timestamp=str(time.time()), sender=Keys.vk)
