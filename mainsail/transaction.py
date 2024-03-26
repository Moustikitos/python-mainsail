# -*- coding: utf-8 -*-

import binascii
import cSecp256k1

from io import BytesIO
from typing import Union, TextIO
from mainsail import serializer, deserializer, identity, rest, cfg
from mainsail import pack, pack_bytes, unpack, unpack_bytes

# bit masks for serialization options
SKIP_SIG1 = 0b100  # skip signature
SKIP_SIG2 = 0b010  # skip second signature
SKIP_MSIG = 0b001  # skip multiple signatures

# list of attributes to be exported
TX_ATTRIBUTES = [
    "amount", "asset", "fee", "id", "network", "recipientId",
    "secondSignature", "senderPublicKey", "signature", "signatures",
    "signSignature", "nonce", "type", "typeGroup", "vendorField",
    "version", "lockTransactionId", "lockSecret", "expiration"
]


class Transaction:
    """
    Generic transaction class.

    Attributes:
        amount (int):
        asset (dict):
        id (str):
        network (int):
        recipientId (str):
        secondSignature (str):
        signature (str):
        signatures (list):
        signSignature (str):
        nonce (int):
        type (int):
        typeGroup (int):
        vendorField (str|bytes):
        version (int):
        lockTransactionId (str):
        lockSecret (str):
        expiration (int):
    """
    APB_MODE: int = 0  # TODO: continue APB_MODE dev

    amount: int = 0
    asset: dict = None
    id: str = None
    network: int = None
    recipientId: str = None
    secondSignature: str = None
    signature: str = None
    signatures: list = None
    signSignature: str = None
    nonce: int = 0
    type: int = None
    typeGroup: int = None
    vendorField: Union[str, bytes] = None
    version: int = 1
    lockTransactionId: str = None
    lockSecret: str = None
    expiration: int = 0

    @property
    def vendorFieldHex(self):
        return self.vendorField

    @vendorFieldHex.setter
    def vendorFieldHex(self, value: str):
        self.vendorField = binascii.unhexlify(value)

    @property
    def fee(self) -> int:
        return getattr(self, "_fee", 10000000)

    @fee.setter
    def fee(self, value: Union[float, str]) -> None:
        # if value is float it is converted into arktoshi
        # if value is str it should starts with either 'min', 'avg' or 'max'
        # TODO: isinstance int -> arktoshi/bytes mode (APB_MODE)
        if isinstance(value, float):
            self._fee = int(value * 100000000)
        elif isinstance(value, str):
            value = value[:3]
            # to match tx name in cfg.fees, lowercase the first char of class
            # name: 'ClassName' -> 'className'
            name = self.__class__.__name__
            name = f"{name[0].lower()}{name[1:]}"
            if value in "minavgmax":
                self._fee = int(
                    getattr(cfg, "fees", {}).get(f"{self.version}", {})
                    .get(name, {}).get(value, '10000000')
                )
        elif isinstance(value, int):
            self.APB_MODE = value

    @property
    def senderId(self) -> str:
        return identity.getWallet(self.senderPublicKey)

    @senderId.setter
    def senderId(self, addr) -> None:
        # get wallet attributes ans store it as `wallet` attribute
        resp = rest.GET.api.wallets(addr)
        if not resp.get("error", False):
            self._wallet = resp
            # update transaction senderPublicKey and nonce
            self._senderPublicKey = resp["publicKey"]
            self.nonce = int(resp["nonce"]) + 1
        else:
            raise rest.ApiError(resp)

    @property
    def senderPublicKey(self) -> str:
        return getattr(self, "_senderPublicKey", None)

    @senderPublicKey.setter
    def senderPublicKey(self, puk) -> None:
        # get wallet attributes ans store it as `wallet` attribute
        resp = rest.GET.api.wallets(puk)
        if not resp.get("error", False):
            self._wallet = resp
            self.nonce = int(resp["nonce"]) + 1
        else:
            self.nonce = 1
        self._senderPublicKey = puk

    def export(self) -> dict:
        """Return a mapping representation of the transaction."""
        result = {}
        for attr in TX_ATTRIBUTES:
            value = getattr(self, attr, None)
            if value is not None:
                result[attr] = value
        return result

    def serialize(self, skip_mask: int = 0b000) -> str:
        """
        Serialize the transaction.

        Arguments:
            skip_mask (int): binary mask to skip signatures during the
                serialization. Available masks are `SKIP_SIG1`, `SIG_SIG2` and
                `SIG_MSIG`.

        Returns:
            str: the serialized transaction as hex string.
        """
        return self.serializeCommon() + self.serializeAsset() + \
            self.serializeSignatures(skip_mask)

    def serializeCommon(self) -> str:
        buf = BytesIO()

        pack("<BBB", buf, (0xff, self.version, cfg.version))
        pack("<IHQ", buf, (self.typeGroup, self.type, self.nonce))
        pack_bytes(buf, binascii.unhexlify(self.senderPublicKey))

        vf_len = getattr(cfg, "constants", {}).get("vendorFieldLength", 255)
        vendorField = (self.vendorField or "")[:vf_len]
        if isinstance(vendorField, str):
            vendorField = vendorField.encode("utf-8")
        pack("<QB", buf, (self.fee, len(vendorField)))
        pack_bytes(buf, vendorField)

        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    @staticmethod
    def deserializeCommon(buf: TextIO) -> dict:
        data = {}
        _, data["version"], _ = unpack("<BBB", buf)
        data["typeGroup"], data["type"], data["nonce"] = unpack("<IHQ", buf)
        data["senderPublicKey"] = \
            binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
        data["fee"], len_vf = unpack("<QB", buf)
        vendorField = unpack_bytes(buf, len_vf)
        try:
            data["vendorField"] = \
                binascii.unhexlify(vendorField).decode("utf-8")
        except binascii.Error:
            data["vendorField"] = vendorField.decode("utf-8")
        return data

    def serializeAsset(self) -> str:
        return getattr(serializer, f"_{self.typeGroup}_{self.type}")(self)

    def deserializeAsset(self, buf: TextIO):
        return getattr(
            deserializer, f"_{self.typeGroup}_{self.type}"
        )(self,)

    def serializeSignatures(self, skip_mask: int) -> str:
        buf = BytesIO()
        if not (skip_mask & SKIP_SIG1) and self.signature:
            pack_bytes(buf, binascii.unhexlify(self.signature))
        if not skip_mask & SKIP_SIG2:
            if self.signSignature:
                pack_bytes(buf, binascii.unhexlify(self.signSignature))
            elif self.secondSignature:
                pack_bytes(buf, binascii.unhexlify(self.secondSignature))
        if not (skip_mask & SKIP_MSIG) and self.signatures:
            pack_bytes(buf, binascii.unhexlify("".join(self.signatures)))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeSignatures(self, buf: TextIO):
        pass  # TODO:

    def sign(
        self, prk: Union[cSecp256k1.Bcrpt410, str, int] = None,
        nonce: int = None
    ) -> None:
        if not isinstance(prk, cSecp256k1.Bcrpt410):
            prk = cSecp256k1.Bcrpt410(prk)
        self.senderPublicKey = prk.puk().encode()
        if nonce:
            self.nonce = nonce
        sig = prk.sign(
            binascii.unhexlify(
                self.serialize(SKIP_SIG1 | SKIP_SIG2)
            )
        ).raw()
        self.signature = sig

    def signSign(
        self, prk2: Union[cSecp256k1.Bcrpt410, str, int] = None
    ) -> None:
        if not isinstance(prk2, cSecp256k1.Bcrpt410):
            prk2 = cSecp256k1.Bcrpt410(prk2)
        sig = prk2.sign(
            binascii.unhexlify(self.serialize(SKIP_SIG2))
        ).raw()
        self.secondSignature = sig

    def multiSign(
        self, prki: Union[cSecp256k1.Bcrpt410, str, int] = None
    ) -> bool:
        if not isinstance(prki, cSecp256k1.Bcrpt410):
            prki = cSecp256k1.Bcrpt410(prki)
        sig = prki.sign(
            binascii.unhexlify(
                self.serialize(SKIP_SIG1 | SKIP_SIG2 | SKIP_MSIG)
            )
        ).raw()
        return self.appendMultiSig(sig, prki.puk().encode())

    def appendMultiSig(self, signature: str, puk: str = None) -> bool:
        hS = cSecp256k1.HexSig.from_raw(signature)
        msg = cSecp256k1.hash_sha256(
            binascii.unhexlify(
                self.serialize(SKIP_SIG1 | SKIP_SIG2 | SKIP_MSIG)
            )
        )
        check = False

        puki = (
            getattr(self, "asset", {}) if self.type == 4 else
            getattr(self, "_wallet", {}).get("attributes", {})
        ).get("multiSignature", {}).get("publicKeys", [])

        if puk is None:
            for puk in puki:
                _puk = cSecp256k1.PublicKey.decode(puk)
                if cSecp256k1._schnorr.bcrypto410_verify(
                    msg, _puk.x, _puk.y, hS.r, hS.s
                ):
                    check = True
                    break
        elif puk in puki:
            _puk = cSecp256k1.PublicKey.decode(puk)
            check = bool(
                cSecp256k1._schnorr.bcrypto410_verify(
                    msg, _puk.x, _puk.y, hS.r, hS.s
                )
            )

        if check is True:
            # TODO: remove previous indexed signature if any
            signature = f"{puki.index(puk):02x}" + signature
            self.signatures = sorted(
                set((self.signatures or []) + [signature]),
                key=lambda s: s[:2]
            )

        return check

    def identify(self) -> None:
        if hasattr(self, "signature") or hasattr(self, "signatures"):
            # TODO: check seconSignature ?
            # TODO: check signatures min ?
            serial = binascii.unhexlify(self.serialize())
            self.id = cSecp256k1.hash_sha256(serial).decode("utf-8")

    def send(self) -> dict:
        return rest.POST.api(
            "transaction-pool", transactions=[self.serialize()]
        )
