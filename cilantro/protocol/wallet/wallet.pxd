cdef extern from "crypto_box.h":
    cdef int crypto_box_keypair(unsigned char *pk, unsigned char *sk);

cdef extern from "crypto_secretbox.h":
    cdef void crypto_secretbox_keygen(unsigned char k[crypto_secretbox_KEYBYTES])
    cdef int crypto_secretbox_easy(unsigned char *c, const unsigned char *m,
                              unsigned long long mlen, const unsigned char *n,
                              const unsigned char *k)

cdef extern from "randombytes.h":
    cdef void randombytes_buf(void * const buf, const size_t size)
