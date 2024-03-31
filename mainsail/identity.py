# -*- coding: utf-8 -*-

import os
import blspy
import pyaes
import base58
import hashlib
import binascii
import cSecp256k1
import unicodedata

from mainsail import cfg
from typing import Union, List


class InvalidDecryption(Exception):
    pass


class InvalidWalletAddress(Exception):
    pass


class InvalidUsername(Exception):
    pass


class KeyRing(cSecp256k1.KeyRing):

    def dump(self, pin: Union[bytes, List[int]]) -> None:
        code = binascii.hexlify(bytes(pin)).decode("utf-8")
        name = binascii.hexlify(bip39_hash(code)).decode("utf-8")
        filename = os.path.join(
            os.path.dirname(__file__), ".keyrings", f"{name[:16]}.krg"
        )
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as output:
            output.write(encrypt(f"{self:064x}", code))

    @staticmethod
    def create(obj: int = None):
        return (
            Schnorr if getattr(cfg, "bip340", False) else Bcrpt410
        )(obj)


class Bcrpt410(KeyRing, cSecp256k1.Bcrpt410):

    @staticmethod
    def load(pin: Union[bytes, List[int]]):
        code = binascii.hexlify(bytes(pin)).decode("utf-8")
        name = binascii.hexlify(bip39_hash(code)).decode("utf-8")
        filename = os.path.join(
            os.path.dirname(__file__), ".keyrings", f"{name[:16]}.krg"
        )
        if os.path.exists(filename):
            with open(filename, "rb") as input:
                data = binascii.unhexlify(decrypt(input.read(), code))
                return Bcrpt410(int.from_bytes(data, "big"))
        else:
            raise InvalidDecryption("no keyring paired with given pin code")


class Schnorr(KeyRing, cSecp256k1.Schnorr):

    @staticmethod
    def load(pin: Union[bytes, List[int]]):
        code = binascii.hexlify(bytes(pin)).decode("utf-8")
        name = binascii.hexlify(bip39_hash(code)).decode("utf-8")
        filename = os.path.join(
            os.path.dirname(__file__), ".keyrings", f"{name[:16]}.krg"
        )
        if os.path.exists(filename):
            with open(filename, "rb") as input:
                data = binascii.unhexlify(decrypt(input.read(), code))
                return Schnorr(int.from_bytes(data, "big"))
        else:
            raise InvalidDecryption("no keyring paired with given pin code")


def bip39_hash(secret: str, passphrase: str = "") -> bytes:
    # bip39 hash method
    # validated on https://iancoleman.io/bip39/
    return hashlib.pbkdf2_hmac(
        "sha512", unicodedata.normalize("NFKD", secret).encode("utf-8"),
        unicodedata.normalize("NFKD", f"mnemonic{passphrase}").encode("utf-8"),
        iterations=2048, dklen=64
    )


def encrypt(data: str, pin: str) -> bytes:
    h = hashlib.sha256(pin.encode("utf-8")).digest()
    aes = pyaes.AESModeOfOperationCTR(h)
    return aes.encrypt(data.encode("utf-8"))


def decrypt(data: bytes, pin: str) -> str:
    h = hashlib.sha256(pin.encode("utf-8")).digest()
    aes = pyaes.AESModeOfOperationCTR(h)
    try:
        return aes.decrypt(data).decode("utf-8")
    except UnicodeDecodeError:
        return False


def combinePublicKey(*puki) -> str:
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
    data: Union[str, bytes], prk: Union[KeyRing, str, int] = None,
    format: str = "raw"
) -> str:
    """
    Compute raw Schnorr signature from data using private key according to
    bcrypto 4.10 spec or BIP340 specification.

    Args:
        data (str|bytes): data used for signature computation.
        prk (str|int|KeyRing): private key or keyring.

    Returns:
        str: Schnorr raw signature (ie r | s)
    """
    if not isinstance(prk, KeyRing):
        prk = KeyRing.create(prk)
    return getattr(
        prk.sign(data.encode("utf-8") if isinstance(data, str) else data),
        format
    )()


def userKeys(secret: Union[int, bytes, str]) -> dict:
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


def validatorKeys(secret: str) -> dict:
    privateKey = blspy.AugSchemeMPL.derive_child_sk(
        blspy.AugSchemeMPL.key_gen(bip39_hash(secret)), 0
    )
    return {
        "validatorPrivateKey": bytes(privateKey).hex(),
        "validatorPublicKey": bytes(privateKey.get_g1()).hex()
    }


def getWIF(seed: bytes) -> str:
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
