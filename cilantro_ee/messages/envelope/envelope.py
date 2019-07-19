from cilantro_ee.utils import lazy_property, set_lazy_property
from cilantro_ee.messages.base.base import MessageBase
from cilantro_ee.messages.envelope.message_meta import MessageMeta
from cilantro_ee.messages.envelope.seal import Seal
from cilantro_ee.protocol.structures.envelope_auth import EnvelopeAuth

import time
from typing import Union

import envelope_capnp

from cilantro_ee.protocol import wallet
from cilantro_ee.utils import Hasher  # Just for debugging (used in __repr__)

class Envelope(MessageBase):
    """
    An Envelope is a structure that packages all messages passed between nodes on the Cilantro network. It surrounds an
    underlying MessageBase instance, and includes features to (de)serialize the message, as well as cryptographic features
    to verify that the message actually originated from the supposed sender.

    An envelope consists of 3 parts:
    1) Seal
        - Contains the sender's signature as well as his verifying key
        - The envelope's metadata binary concatenated with the message binary is what gets actually signed
    2) MessageMeta
        - Contains the Envelope's (hopefully) unique UUID, which gets randomly generated when the envelope is created
        - Contains the Envelope's timestamp, i.e. the time that the envelope was created
        - Contains the Message's 'type', which is an enum representing the Message's Python class. This is used for
          deserialization
    3) Message
        - The actual MessageBase instance inside the envelope. This is what actually gets fed into the StateMachines
    """

    @classmethod
    def _deserialize_data(cls, data: bytes):
        return envelope_capnp.Envelope.from_bytes_packed(data)

    @classmethod
    def from_bytes(cls, data: bytes, validate=True, cache_binary=True):
        env = cls.from_bytes(data=data, validate=validate)

        if cache_binary:
            set_lazy_property(env, 'serialize', data)

        return env

    @classmethod
    def create_from_message(cls, message: MessageBase, signing_key: str, verifying_key: str=None, uuid: int=-1):
        """
        Creates an Envelope to package a MessageBase instance

        :param message: The MessageBase instance to create an envelope for
        :param signing_key: The sender's signing key, which is used to create the Seal.
        :param verifying_key: The sender's verifying key. This should be passed in for computational efficiency, but
        can be computed from the signing key if it is ommited
        :param uuid: The UUID to use for the Envelope's MessageMeta. If -1, a random UUID will be generated.
        :return: An Envelope instance
        """
        assert issubclass(type(message), MessageBase), "message arg must be a MessageBase subclass"
        # assert type(message) in MessageBase.registry, "Message type {} not found in registry {}"\
        #     .format(type(message), MessageBase.registry)
        # TODO -- verify sk (valid hex, 128 char)

        # Create MessageMeta
        t = 0
        timestamp = str(time.time())
        meta = MessageMeta.create(type=t, timestamp=timestamp, uuid=uuid)

        # Create Seal
        if not verifying_key:
            verifying_key = wallet.get_vk(signing_key)
        seal_sig = EnvelopeAuth.seal(signing_key=signing_key, meta=meta, message=message)
        seal = Seal.create(signature=seal_sig, verifying_key=verifying_key)

        # Create Envelope
        obj = cls._create_from_objects(seal=seal, meta=meta, message=message.serialize())
        set_lazy_property(obj, 'message', message)

        return obj

    @classmethod
    def _create_from_objects(cls, seal: Seal, meta: MessageMeta, message: bytes):
        assert type(message) is bytes, "Message arg must be bytes"
        data = envelope_capnp.Envelope.new_message()
        data.seal = seal._data
        data.meta = meta._data
        data.message = message

        obj = cls.from_data(data, validate=False)

        set_lazy_property(obj, 'seal', seal)
        set_lazy_property(obj, 'meta', meta)

        return obj

    def validate(self):
        # Any of these 3 lines will throw an exception if the seal/meta/message cannot be deserialized
        assert self.seal
        assert self.meta
        assert self.message

        assert self.verify_seal(), "Seal is invalid!"

    def verify_seal(self) -> bool:
        """
        Validates the cryptographic signature on the envelope's seal. The signature should be the MessageMeta binary
        concatenated with the MessageBase binary signed by the sender.

        :return: A bool, True is the Seal's signature is valid, and False otherwise
        """
        return EnvelopeAuth.verify_seal(seal=self.seal, meta=self.meta_binary, message=self.message_binary)

    @property
    def message_binary(self) -> bytes:
        return self._data.message

    @lazy_property
    def meta_binary(self) -> bytes:
        return self.meta.serialize()

    @lazy_property
    def seal(self) -> Seal:
        return Seal.from_data(self._data.seal)

    @lazy_property
    def meta(self) -> MessageMeta:
        return MessageMeta.from_data(self._data.meta)

    @lazy_property
    def message(self) -> MessageBase:
        # assert self.meta.type in MessageBase.registry, "Type {} not found in registry {}"\
        #     .format(self.meta.type, MessageBase.registry)

        return self.meta.from_bytes(self.message_binary)

    @lazy_property
    def message_hash(self) -> str:
        return Hasher.hash(self.message)

    @property
    def sender(self) -> str:
        """
        Returns the verifying key of the sender of this envelope
        """
        return self.seal.verifying_key

    def is_from_group(self, groups: Union[list, str]) -> bool:
        """
        Returns True if this envelope is from a group of 
        :param groups: A str, representing a type from enum NodeTypes, or a list of a said strings
        :return: True if this envelope is from a sender who belongs to the specified groups, False otherwise
        """
        from cilantro_ee.nodes.base import NodeTypes  # To avoid cyclic imports (i apologize for my sins --davis)

        if type(groups) is str:
            groups = (groups,)

        for g in groups:
            if NodeTypes.check_vk_in_group(vk=self.sender, group=g):
                return True

        return False

    def __repr__(self):
        """
        Printing the full capnp struct (which is the default MessageBase __repr__ behvaior) is way to verbose for
        the logs. Here we just slim this guy down a little to make the logs easier to read
        TODO -- the hashing bit should not be done in production as this wastes computational cycles
        """
        msg_type = str(MessageBase.registry[self.meta.type])
        msg_hash = Hasher.hash(data=self.message_binary, digest_len=3)  # compressed representation of the message
        seal_vk = self.seal.verifying_key
        uuid = self.meta.uuid

        rep = "\nEnvelope from sender {}".format(seal_vk)
        rep += "\n\tuuid: {}".format(uuid)
        rep += "\n\tmessage type: {}".format(msg_type)
        rep += "\n\tmessage hash: {}".format(msg_hash)

        return rep

