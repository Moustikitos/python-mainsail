# -*- coding: utf-8 -*-

import base58
import hashlib
import binascii
import cSecp256k1

from mainsail import cfg


def combinePublicKey(*puki):
    P = cSecp256k1.PublicKey.decode(puki[0])
    for puk in puki[1:]:
        P += cSecp256k1.PublicKey.decode(puk)
    return P.encode()


def getWallet(puk: str, version: int = None) -> str:
    ripemd160 = hashlib.new('ripemd160', binascii.unhexlify(puk)).digest()[:20]
    seed = binascii.unhexlify(f"{version or cfg.version:02x}") + ripemd160
    b58 = base58.b58encode_check(seed)
    return b58.decode('utf-8') if isinstance(b58, bytes) else b58
