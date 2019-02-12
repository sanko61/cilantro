from zmq.utils.z85 import encode
from nacl.signing import SigningKey, VerifyKey
from nacl.bindings import crypto_sign_ed25519_sk_to_curve25519
import hashlib

class Keys:
    _is_setup = False
    @classmethod
    def setup(cls, sk_hex):
        # assert not cls._is_setup, 'Can only import SK once per process'
        nacl_sk = SigningKey(seed=bytes.fromhex(sk_hex))
        cls.sk = sk_hex
        cls.vk = nacl_sk.verify_key.encode().hex()
        cls.public_key = cls.vk2pk(cls.vk)
        cls.private_key = crypto_sign_ed25519_sk_to_curve25519(nacl_sk._signing_key)
        cls._is_setup = True

    @staticmethod
    def vk2pk(vk):
        return encode(VerifyKey(bytes.fromhex(vk)).to_curve25519_public_key()._public_key)

    @staticmethod
    def digest(s):
        if not isinstance(s, bytes):
            s = str(s).encode('utf8')
        return hashlib.sha1(s).digest()


if __name__ == '__main__':
    pass