# -*- coding: utf-8 -*-

import base58
import hashlib
import binascii
import cSecp256k1

from mainsail import cfg
from typing import Union


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


def sign(
    data: Union[str, bytes], prk: Union[cSecp256k1.Bcrpt410, str, int] = None
) -> str:
    """
    Compute raw Schnorr signature from data using private key according to
    bcrypto 4.10 spec.

    Args:
        data (str|bytes): data used for signature computation.
        prk (str|int|cSecp256k1.Bcrpt410): private key or keyring.

    Returns:
        str: Schnorr raw signature (ie r | s)
    """
    if not isinstance(prk, cSecp256k1.Bcrpt410):
        prk = cSecp256k1.Bcrpt410(prk)
    return prk.sign(
        data.encode("utf-8") if isinstance(data, str) else data
    ).raw()
