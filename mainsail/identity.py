# -*- coding: utf-8 -*-

import blspy
import base58
import hashlib
import binascii
import cSecp256k1
import unicodedata

from mainsail import cfg
from typing import Union


class InvalidWalletAddress(Exception):
    pass


class InvalidUsername(Exception):
    pass


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


def getKeys(secret):
    """
    Generate keyring containing secp256k1 keys-pair and wallet import format
    (WIF).

    Args:
        secret (str, bytes or int): anything that could issue a private key on
            secp256k1 curve.

    Returns:
        dict: public, private and WIF keys.
    """
    if isinstance(secret, int):
        privateKey = "%064x" % secret
        seed = binascii.unhexlify(privateKey)
    elif isinstance(secret, (bytes, str)):
        privateKey = cSecp256k1.hash_sha256(secret).decode("utf-8")
        seed = binascii.unhexlify(privateKey)

    return {
        "publicKey": cSecp256k1.PublicKey.from_seed(seed).encode(),
        "privateKey": privateKey,
        "wif": getWIF(seed)
    }


def validatorKeys(secret: str):
    try:
        # bip39 hash method without salt passphrase
        # validated on https://iancoleman.io/bip39/
        seed = hashlib.pbkdf2_hmac(
            "sha512", unicodedata.normalize("NFKD", secret).encode("utf-8"),
            unicodedata.normalize("NFKD", "mnemonic").encode("utf-8"),
            iterations=2048, dklen=64
        )
    except Exception:
        return {}
    else:
        privateKey = blspy.AugSchemeMPL.derive_child_sk(
            blspy.AugSchemeMPL.key_gen(seed), 0
        )
        return {
            "validatorPrivateKey": bytes(privateKey).hex(),
            "validatorPublicKey": bytes(privateKey.get_g1()).hex()
        }


def getWIF(seed):
    """
    Compute WIF address from seed.

    Args:
        seed (bytes): a sha256 sequence bytes.

    Returns:
        base58: the WIF address.
    """
    if hasattr(cfg, "wif"):
        seed = binascii.unhexlify(f"{cfg.wif:02x}") + seed[:32] + b"\x01"
        b58 = base58.b58encode_check(seed)               # \x01 -> compressed
        return b58.decode('utf-8') if isinstance(b58, bytes) else b58
