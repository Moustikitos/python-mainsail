# -*- coding: utf-8 -*-

import re
import sys
import base58
import getpass
import binascii
import cSecp256k1

from io import BytesIO
from typing import TextIO, Union
from mainsail.transaction import (
    Transaction, pack, pack_bytes, unpack, unpack_bytes, rest
)
from mainsail import cfg, identity, TYPE_GROUPS, TYPES


def deserialize(serial: str):
    buf = BytesIO(binascii.unhexlify(serial))
    data = Transaction.deserializeCommon(buf)
    # transform TYPES enum name to class name
    name = "".join(e.capitalize() for e in TYPES(data["type"]).name.split("_"))
    # get transaction builder class
    tx = getattr(sys.modules[__name__], name)()
    for key, value in data.items():
        setattr(tx, key, value)
    tx.deserializeAsset(buf)
    tx.deserializeSignatures(buf)
    return tx


class Transfer(Transaction):

    def __init__(
        self, amount: float, recipientId: str,
        vendorField: Union[str, bytes] = None
    ) -> None:
        try:
            base58.b58decode_check(recipientId)
        except ValueError:
            raise identity.InvalidWalletAddress(
                f"recipientId '{recipientId}' is not a valid wallet address"
            )
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.TRANSFER.value
        self.fee = "avg"

        self.amount = int(amount * 100000000)
        self.recipientId = recipientId
        if vendorField is not None:
            self.vendorField = vendorField

    def serializeAsset(self) -> str:
        buf = BytesIO()
        pack("<QI", buf, (self.amount, self.expiration))
        pack_bytes(buf, base58.b58decode_check(self.recipientId))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeAsset(self, buf: TextIO):
        self.amount, self.expiration = unpack("<QI", buf)
        recipientId = base58.b58encode_check(unpack_bytes(buf, 21))
        self.recipientId = recipientId.decode("utf-8")


class ValidatorRegistration(Transaction):

    def __init__(self, validator: str = None):
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.VALIDATOR_REGISTRATION.value
        self.fee = "avg"

    def sign(self, mnemonic: str = None, nonce: int = None) -> None:
        if mnemonic is None:
            mnemonic = getpass.getpass(
                "Type or paste your bip39 passphrase > "
            )
        puk = identity.validatorKeys(mnemonic).get("validatorPublicKey", None)
        if puk:
            self.asset = {"validatorPublicKey": puk}
            Transaction.sign(self, mnemonic, nonce)
        else:
            raise Exception()

    def serializeAsset(self):
        buf = BytesIO()
        pack_bytes(buf, binascii.unhexlify(self.asset["validatorPublicKey"]))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")


class Vote(Transaction):

    def __init__(self, validator: str = None):
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.VOTE.value
        self.fee = "avg"

        self.asset = {"unvotes": [], "votes": []}
        if validator is not None:
            self.upVote(validator)

    def checkAsset(self):
        prev_puk = getattr(self, "_wallet", {}).get("vote", None)
        if prev_puk is not None and len(self.asset["votes"]):
            self.asset["unvotes"] = [prev_puk]

    def upVote(self, validator: str) -> None:
        puk = rest.GET.api.wallets(validator).get("publicKey")
        if puk not in self.asset["votes"]:
            self.asset["votes"] = [puk]
            self.checkAsset()

    def downVote(self, validator: str) -> None:
        puk = rest.GET.api.wallets(validator).get("publicKey")
        self.asset["unvotes"] = [puk]

    def serializeAsset(self):
        buf = BytesIO()
        pack("<B", buf, (len(self.asset["votes"]), ))
        pack_bytes(buf, binascii.unhexlify("".join(self.asset["votes"])))
        pack("<B", buf, (len(self.asset["unvotes"]), ))
        pack_bytes(buf, binascii.unhexlify("".join(self.asset["unvotes"])))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeAsset(self, buf: TextIO):
        n, = unpack("<B", buf)
        self.asset["votes"] = [
            binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
            for i in range(n)
        ]
        n, = unpack("<B", buf)
        self.asset["unvotes"] = [
            binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
            for i in range(n)
        ]


class MultiSignature(Transaction):

    def __init__(self, *puki, minimum: int = 2) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.MULTI_SIGNATURE.value
        self.fee = "avg"

        self.asset = {
            "multiSignature": {"min": minimum, "publicKeys": list(puki)}
        }
        self.setRecipient()

    def setRecipient(self):
        self.recipientId = identity.getWallet(
            identity.combinePublicKey(
                cSecp256k1.PublicKey.from_secret(
                    f"{self.asset['multiSignature']['min']:02x}"
                ).encode(), *self.asset["multiSignature"]["publicKeys"]
            )
        )

    def addParticipant(self, puk: str):
        self.asset["multiSignature"]["publicKeys"].append(puk)
        self.setRecipient()

    def minRequired(self, minimum: int = 2):
        self.asset["multiSignature"]["min"] = minimum
        self.setRecipient()

    def serializeAsset(self) -> str:
        buf = BytesIO()
        pack(
            "<BB", buf, (
                self.asset["multiSignature"]["min"],
                len(self.asset["multiSignature"]["publicKeys"]),
            )
        )
        for puk in self.asset["multiSignature"]["publicKeys"]:
            pack_bytes(buf, binascii.unhexlify(puk))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeAsset(self, buf: TextIO):
        self.asset["multiSignature"]["min"], n = unpack("<BB", buf)
        self.asset["multiSignature"]["publicKeys"] = [
            binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
            for i in range(n)
        ]


class MultiPayment(Transaction):

    def __init__(self, vendorField: str = None, **payments) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.MULTI_PAYMENT.value
        self.fee = "avg"

        self.asset = {"payments": []}
        if vendorField is not None:
            self.vendorField = vendorField
        for address, amount in payments.items():
            self.addPayment(amount, address)

    def addPayment(self, amount: float, address: str):
        amount = int(amount * 100000000)
        self.asset["payments"].append(
            {"recipientId": address, "amount": amount}
        )
        self.amount += amount

    def serializeAsset(self) -> str:
        buf = BytesIO()
        pack("<H", buf, (len(self.asset["payments"]), ))
        for item in self.asset["payments"]:
            pack("<Q", buf, (item["amount"], ))
            pack_bytes(buf, base58.b58decode_check(item["recipientId"]))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeAsset(self, buf: TextIO):
        n, = unpack("<H", buf)
        for i in range(n):
            amount, = unpack("<Q", buf)
            address, = base58.b58encode_check(unpack_bytes(buf, 21))
            self.assets["payments"][i] = {
                "recipientId": address.decode("utf-8"), "amount": amount
            }


class ValidatorResignation(Transaction):
    pass


class UsernameRegistration(Transaction):

    def __init__(self, username: str = None) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(cfg, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.USERNAME_REGISTRATION.value
        self.fee = "avg"

        if username is not None:
            self.setUsername(username)

    def setUsername(self, username: str) -> None:
        if re.match('^(?!_)(?!.*_$)(?!.*__)[a-z0-9_]+$', username) is None \
                and len(username) > 20 or len(username) < 1:
            raise identity.InvalidUsername("invalid username")
        self.asset = {"username": username}

    def serializeAsset(self):
        buf = BytesIO()
        pack("<B", buf, (len(self.asset["username"]), ))
        pack_bytes(buf, self.asset["username"].encode("utf-8"))
        return binascii.hexlify(buf.getvalue()).decode("utf-8")

    def deserializeAsset(self, buf: TextIO):
        n, = unpack("<B", buf)
        self.asset = {"username": unpack_bytes(buf, n).decode("utf-8")}


class UsernameResignation(Transaction):
    pass
