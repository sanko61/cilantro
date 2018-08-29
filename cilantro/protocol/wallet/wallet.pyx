cimport wallet

cdef generate_keys():
    cdef extern unsigned char pk[crypto_sign_PUBLICKEYBYTES]
    cdef extern unsigned char sk[crypto_sign_SECRETKEYBYTES]
    return wallet.crypto_box_keypair(pk, sk)
