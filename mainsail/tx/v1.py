# -*- coding: utf-8 -*-

import re
import sys
import base58
import getpass
import binascii
import cSecp256k1

from io import BytesIO
from typing import Union
from mainsail.transaction import Transaction
from mainsail import config, rest, identity, TYPE_GROUPS, TYPES

__all__ = [
    "Transfer", "ValidatorRegistration", "ValidatorResignation",
    "UsernameRegistration", "UsernameResignation", "Vote", "MultiPayment",
    "MultiSignature"
]


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
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.TRANSFER.value
        self.fee = "avg"

        self.amount = int(amount * 100000000)
        self.recipientId = recipientId
        if vendorField is not None:
            self.vendorField = vendorField


class ValidatorRegistration(Transaction):

    def __init__(self, validator: str = None):
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
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


class Vote(Transaction):

    def __init__(self, validator: str = None):
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.VOTE.value
        self.fee = "avg"

        self.asset = {"unvotes": [], "votes": []}
        if validator is not None:
            self.upVote(validator)

    def checkAsset(self):
        prev_puk = getattr(
            self, "_wallet", {}
        ).get("attributes", {}).get("vote", None)
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


class MultiSignature(Transaction):

    def __init__(self, *puki, minimum: int = 2) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
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


class MultiPayment(Transaction):

    def __init__(self, vendorField: str = None, **payments) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
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


class ValidatorResignation(Transaction):

    def __init__(self) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.VALIDATOR_RESIGNATION.value
        self.fee = "avg"


class UsernameRegistration(Transaction):

    def __init__(self, username: str = None) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
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


class UsernameResignation(Transaction):

    def __init__(self) -> None:
        Transaction.__init__(self)
        self.version = \
            getattr(config, "consants", {}).get("block", {}).get("version", 1)
        self.typeGroup = TYPE_GROUPS.CORE.value
        self.type = TYPES.USERNAME_RESIGNATION.value
        self.fee = "avg"
