"""Minimal libsodium sealed-box (X25519 + XSalsa20-Poly1305), pure Python.

GitHub Actions secrets must be encrypted this way; no libsodium binding is
available in this sandbox, so the primitives are assembled from
`cryptography` (X25519) and `pycryptodome` (Salsa20 / Poly1305).
"""
import hashlib
import os
import struct

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from Crypto.Cipher import Salsa20
from Crypto.Hash import Poly1305

SIGMA = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)
MASK = 0xFFFFFFFF


def _rotl(a, b):
    return ((a << b) | (a >> (32 - b))) & MASK


def salsa20_rounds(x):
    """20 rounds without feeding the input back (HSalsa20 core)."""
    x = list(x)
    for _ in range(10):
        x[4] ^= _rotl((x[0] + x[12]) & MASK, 7)
        x[8] ^= _rotl((x[4] + x[0]) & MASK, 9)
        x[12] ^= _rotl((x[8] + x[4]) & MASK, 13)
        x[0] ^= _rotl((x[12] + x[8]) & MASK, 18)
        x[9] ^= _rotl((x[5] + x[1]) & MASK, 7)
        x[13] ^= _rotl((x[9] + x[5]) & MASK, 9)
        x[1] ^= _rotl((x[13] + x[9]) & MASK, 13)
        x[5] ^= _rotl((x[1] + x[13]) & MASK, 18)
        x[14] ^= _rotl((x[10] + x[6]) & MASK, 7)
        x[2] ^= _rotl((x[14] + x[10]) & MASK, 9)
        x[6] ^= _rotl((x[2] + x[14]) & MASK, 13)
        x[10] ^= _rotl((x[6] + x[2]) & MASK, 18)
        x[3] ^= _rotl((x[15] + x[11]) & MASK, 7)
        x[7] ^= _rotl((x[3] + x[15]) & MASK, 9)
        x[11] ^= _rotl((x[7] + x[3]) & MASK, 13)
        x[15] ^= _rotl((x[11] + x[7]) & MASK, 18)
        x[1] ^= _rotl((x[0] + x[3]) & MASK, 7)
        x[2] ^= _rotl((x[1] + x[0]) & MASK, 9)
        x[3] ^= _rotl((x[2] + x[1]) & MASK, 13)
        x[0] ^= _rotl((x[3] + x[2]) & MASK, 18)
        x[6] ^= _rotl((x[5] + x[4]) & MASK, 7)
        x[7] ^= _rotl((x[6] + x[5]) & MASK, 9)
        x[4] ^= _rotl((x[7] + x[6]) & MASK, 13)
        x[5] ^= _rotl((x[4] + x[7]) & MASK, 18)
        x[11] ^= _rotl((x[10] + x[9]) & MASK, 7)
        x[8] ^= _rotl((x[11] + x[10]) & MASK, 9)
        x[9] ^= _rotl((x[8] + x[11]) & MASK, 13)
        x[10] ^= _rotl((x[9] + x[8]) & MASK, 18)
        x[12] ^= _rotl((x[15] + x[14]) & MASK, 7)
        x[13] ^= _rotl((x[12] + x[15]) & MASK, 9)
        x[14] ^= _rotl((x[13] + x[12]) & MASK, 13)
        x[15] ^= _rotl((x[14] + x[13]) & MASK, 18)
    return x


def hsalsa20(key: bytes, nonce16: bytes) -> bytes:
    assert len(key) == 32 and len(nonce16) == 16
    x = [0] * 16
    x[0], x[5], x[10], x[15] = SIGMA
    for i in range(4):
        x[1 + i] = struct.unpack_from("<I", key, i * 4)[0]
        x[11 + i] = struct.unpack_from("<I", key, 16 + i * 4)[0]
        x[6 + i] = struct.unpack_from("<I", nonce16, i * 4)[0]
    out = salsa20_rounds(x)          # HSalsa20: NO feed-forward
    return struct.pack(
        "<8I", out[0], out[5], out[10], out[15], out[6], out[7], out[8], out[9]
    )


def _keystream(key: bytes, nonce24: bytes, nbytes: int) -> bytes:
    sub = hsalsa20(key, nonce24[:16])
    return Salsa20.new(key=sub, nonce=nonce24[16:24]).encrypt(b"\x00" * nbytes)


_P1305_P = (1 << 130) - 5
_P1305_RMASK = 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF


def _num(b: bytes) -> int:
    v = 0
    for i, x in enumerate(b):
        v |= x << (8 * i)
    return v


def _poly1305(key32: bytes, msg: bytes) -> bytes:
    """RFC 8439 Poly1305 with a raw one-time key (no AES/ChaCha20 wrapper)."""
    r = _num(key32[:16]) & _P1305_RMASK
    s = _num(key32[16:32])
    a = 0
    for off in range(0, len(msg), 16):
        blk = msg[off:off + 16]
        n = _num(blk + b"\x01" + b"\x00" * (16 - len(blk)))
        a = ((a + n) * r) % _P1305_P
    acc = (a + s) % (1 << 128)
    return bytes((acc >> (8 * i)) & 0xFF for i in range(16))


def crypto_box_seal(recipient_pk_bytes: bytes, plaintext: bytes) -> bytes:
    eph = X25519PrivateKey.generate()
    eph_pk = eph.public_key().public_bytes_raw()
    shared = eph.exchange(X25519PublicKey.from_public_bytes(recipient_pk_bytes))
    nonce = hashlib.blake2b(eph_pk + recipient_pk_bytes, digest_size=24).digest()
    ks = _keystream(shared, nonce, 64 + len(plaintext))
    poly_key = ks[:32]
    ct = bytes(a ^ b for a, b in zip(plaintext, ks[64:]))
    tag = _poly1305(poly_key, ct)
    return eph_pk + tag + ct


def crypto_box_seal_open(sk_bytes: bytes, pk_bytes: bytes, sealed: bytes) -> bytes:
    eph_pk, tag, ct = sealed[:32], sealed[32:48], sealed[48:]
    sk = X25519PrivateKey.from_private_bytes(sk_bytes)
    shared = sk.exchange(X25519PublicKey.from_public_bytes(eph_pk))
    nonce = hashlib.blake2b(eph_pk + pk_bytes, digest_size=24).digest()
    ks = _keystream(shared, nonce, 64 + len(ct))
    if _poly1305(ks[:32], ct) != tag:
        raise ValueError("authentication failed")
    return bytes(a ^ b for a, b in zip(ct, ks[64:]))
