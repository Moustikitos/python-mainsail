# -*- coding: utf-8 -*-

"""
This modules provides cryptographic primitives to interact with blockchain.

```python
>>> from mainsail import identity
```
"""

import os
import blspy
import pyaes
import base58
import hashlib
import binascii
import cSecp256k1
import unicodedata

from mainsail import config
from typing import Union, List

DATA = os.path.join(os.getenv("HOME"), ".mainsail", ".keyrings")


def _encryption_file_path(code: str) -> str:
    # Returns signer _encryption file path
    name = binascii.hexlify(bip39_hash(code)).decode("utf-8")
    return os.path.join(DATA, f"{name[:32]}.krg")


def _encrypt(data: str, pin: str) -> bytes:
    # Encrypt data according to pin code
    h = hashlib.sha256(pin.encode("utf-8")).digest()
    aes = pyaes.AESModeOfOperationCTR(h)
    return aes.encrypt(data.encode("utf-8"))


def _decrypt(data: bytes, pin: str) -> str:
    # Decrypt data according to pin code
    h = hashlib.sha256(pin.encode("utf-8")).digest()
    aes = pyaes.AESModeOfOperationCTR(h)
    try:
        return aes.decrypt(data).decode("utf-8")
    except UnicodeDecodeError:
        return False


class InvalidSeed(Exception):
    pass


class InvalidDecryption(Exception):
    pass


class InvalidWalletAddress(Exception):
    pass


class InvalidUsername(Exception):
    pass


class KeyRing(cSecp256k1.KeyRing):
    """
    Subclass of `cSecp256K1.KeyRing` allowing secure filesystem saving and
    loading. It is also linked to mainsail network configuration to select
    appropriate Schnorr signature specification (bcrypto 4.10 or BIP 340) to be
    applied.

    ```python
    >>> import os
    >>> signer = identity.KeyRing.create(int.from_bytes(os.urandom(32)))
    >>> signer  # KeyRing is a subclass of builtin int
    40367812022907163119325945335177282621496014100307111368749805816184299969\
919
    >>> sig = signer.sign("simple message")
    >>> puk = signer.puk()  # compute associated public key
    >>> signer.verify(puk, "simple message", sig)
    True
    >>> type(signer)  # bcrypto 4.10 specification used
    <class 'mainsail.identity.Bcrpt410'>
    ```
    """

    @staticmethod
    def path(pin: Union[bytes, List[int]]) -> str:
        code = binascii.hexlify(bytes(pin))
        return _encryption_file_path(code.decode("utf-8"))

    def dump(self, pin: Union[bytes, List[int]]) -> None:
        """
        Securely dump `KeyRing` into filesystem using pin code. Override
        existing file if any.

        Args:
            pin (bytes|List[int]): pin code used to _encrypt KeyRing. Pin code
                may be a list of short (0 < int < 255) or a bytes string.

        ```python
        >>> signer.dump([0, 0, 0, 0])  # dump into filesystem using pin 0000
        >>> signer.dump(b"\\x00\\x00\\x00\\x00")  # equivalent
        ```
        """
        code = binascii.hexlify(bytes(pin))
        filename = _encryption_file_path(code.decode("utf-8"))
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as output:
            code = hashlib.sha256(code).hexdigest()
            output.write(_encrypt(f"{self:064x}", code))

    @staticmethod
    def load(pin: Union[bytes, List[int]]):
        """
        Securely load KeyRing from filesystem using pin code.

        Args:
            pin (bytes|List[int]): pin code used to _encrypt KeyRing. Pin code
                may be a list of short (0 < int < 255) or a bytes string.

        Returns:
            Schnorr|Bcrpt410: signer object.

        ```python
        >>> identity.KeyRing.load([0, 0, 0, 0])
        4036781202290716311932594533517728262149601410030711136874980581618429\
9969919
        >>> identity.KeyRing.load(b"\\x00\\x00\\x00\\x00")
        4036781202290716311932594533517728262149601410030711136874980581618429\
9969919
        ```
        """
        code = binascii.hexlify(bytes(pin))
        filename = _encryption_file_path(code.decode("utf-8"))
        if os.path.exists(filename):
            with open(filename, "rb") as input:
                code = hashlib.sha256(code).hexdigest()
                data = binascii.unhexlify(_decrypt(input.read(), code))
                return get_signer()(int.from_bytes(data, "big"))
        else:
            raise InvalidDecryption("no keyring paired with given pin code")

    @staticmethod
    def create(obj: int = None):
        """
        Create a `KeyRing` signer subclass with the appropriate schnorr
        signature specification.

        Args:
            obj (int): the value of the private key.

        Returns:
            Schnorr|Bcrpt410: signer object.
        """
        return get_signer()(obj)


class Schnorr(cSecp256k1.Schnorr, KeyRing):
    pass


class Bcrpt410(cSecp256k1.Bcrpt410, KeyRing):
    pass


def get_signer():
    "Returns the the network appropriate signer."
    # TODO: adapt according mainsail development
    return Schnorr if getattr(config, "bip340", False) else Bcrpt410


def bip39_hash(secret: str, passphrase: str = "") -> bytes:
    """
    Returns bip39 hash bytes string. This function does not check mnemonic
    integrity.

    Args:
        secret (str): a mnemonic string.
        passphrase (str): salt string.

    Returns:
        bytes: 64 length bytes string.
    """
    return hashlib.pbkdf2_hmac(
        "sha512", unicodedata.normalize("NFKD", secret).encode("utf-8"),
        unicodedata.normalize("NFKD", f"mnemonic{passphrase}").encode("utf-8"),
        iterations=2048, dklen=64
    )


def combine_puk(*puki) -> str:
    P = cSecp256k1.PublicKey.decode(puki[0])
    for puk in puki[1:]:
        if isinstance(puk, str):
            puk = cSecp256k1.PublicKey.decode(puk)
        P += puk
    return P.encode()


def get_wallet(puk: str, version: int = None) -> str:
    ripemd160 = hashlib.new('ripemd160', binascii.unhexlify(puk)).digest()[:20]
    seed = binascii.unhexlify(f"{version or config.version:02x}") + ripemd160
    b58 = base58.b58encode_check(seed)
    return b58.decode('utf-8') if isinstance(b58, bytes) else b58


def sign(
    data: Union[str, bytes], prk: Union[KeyRing, List[int], str, int] = None,
    format: str = "raw"
) -> str:
    """
    Compute Schnorr signature from data using private key according to bcrypto
    4.10 spec or BIP340 specification. Signature format is RAW by defaul but
    can also be specified a DER.

    ```python
    >>> prk = identity.KeyRing.load([0,0,0,0])
    >>> identity.sign("simple message", [0, 0, 0, 0])
    '5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f\
5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
    >>> identity.sign("simple message", prk)
    '5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f\
5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
    >>> identity.sign("simple message", 40367812022907163119325945335177282621\
496014100307111368749805816184299969919)
    '5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f\
5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
    >>> identity.sign("simple message", prk, "der")
    '304402205993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd00\
220026ed229f5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
    ```

    Args:
        data (str|bytes): data used for signature computation.
        prk (KeyRing|List[int]|str|int): private key, keyring or pin code.
        format (str): `raw` or `der` to determine signature format output.

    Returns:
        str: Schnorr signature in raw format (ie r | s) by default.
    """
    if isinstance(prk, list):
        prk = KeyRing.load(prk)
    elif not isinstance(prk, KeyRing):
        prk = KeyRing.create(prk)
    return getattr(
        prk.sign(data.encode("utf-8") if isinstance(data, str) else data),
        format
    )()


def user_keys(secret: Union[int, str]) -> dict:
    """
    Generate keyring containing secp256k1 keys-pair and wallet import format
    (WIF).

    Args:
        secret (str|int): anything that could issue a private key on secp256k1
            curve.

    Returns:
        dict: public, private and WIF keys.
    """
    if isinstance(secret, int):
        privateKey = "%064x" % secret
    elif isinstance(secret, str):
        privateKey = cSecp256k1.hash_sha256(secret).decode("utf-8")
    seed = binascii.unhexlify(privateKey)

    return {
        "publicKey": cSecp256k1.PublicKey.from_seed(seed).encode(),
        "privateKey": privateKey,
        "wif": wif_keys(seed)
    }


def validator_keys(secret: str) -> dict:
    privateKey = blspy.AugSchemeMPL.derive_child_sk(
        blspy.AugSchemeMPL.key_gen(bip39_hash(secret)), 0
    )
    return {
        "validatorPrivateKey": bytes(privateKey).hex(),
        "validatorPublicKey": bytes(privateKey.get_g1()).hex()
    }


def wif_keys(seed: bytes) -> Union[str, None]:
    """
    Compute WIF key from seed.

    Args:
        seed (bytes): a 32 length bytes string.

    Returns:
        str: the WIF key.
    """
    try:
        if len(seed) == 32:
            seed = binascii.unhexlify(f"{config.wif:02x}") + seed + b"\x01"
            b58 = base58.b58encode_check(seed)             # \x01 -> compressed
            return b58.decode('utf-8') if isinstance(b58, bytes) else b58
        else:
            raise InvalidSeed(
                "seed have to be a 32 length bytes string "
                f"(got {len(bytes)} bytes)"
            )
    except AttributeError:
        raise AttributeError("wif attribute is not set in config module")
