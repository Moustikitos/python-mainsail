# -*- coding: utf-8 -*-

import base58
import binascii
from io import BytesIO
from mainsail import pack, pack_bytes


def _1_0(cls) -> str:
    buf = BytesIO()
    pack("<QI", buf, (cls.amount, cls.expiration))
    pack_bytes(buf, base58.b58decode_check(cls.recipientId))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_2(cls) -> str:
    buf = BytesIO()
    pack_bytes(buf, binascii.unhexlify(cls.asset["validatorPublicKey"]))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_3(cls) -> str:
    buf = BytesIO()
    pack("<B", buf, (len(cls.asset["votes"]), ))
    pack_bytes(buf, binascii.unhexlify("".join(cls.asset["votes"])))
    pack("<B", buf, (len(cls.asset["unvotes"]), ))
    pack_bytes(buf, binascii.unhexlify("".join(cls.asset["unvotes"])))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_4(cls) -> str:
    buf = BytesIO()
    pack(
        "<BB", buf, (
            cls.asset["multiSignature"]["min"],
            len(cls.asset["multiSignature"]["publicKeys"]),
        )
    )
    for puk in cls.asset["multiSignature"]["publicKeys"]:
        pack_bytes(buf, binascii.unhexlify(puk))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_6(cls) -> str:
    buf = BytesIO()
    pack("<H", buf, (len(cls.asset["payments"]), ))
    for item in cls.asset["payments"]:
        pack("<Q", buf, (item["amount"], ))
        pack_bytes(buf, base58.b58decode_check(item["recipientId"]))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_7(cls) -> str:
    return ""


def _1_8(cls) -> str:
    buf = BytesIO()
    pack("<B", buf, (len(cls.asset["username"]), ))
    pack_bytes(buf, cls.asset["username"].encode("utf-8"))
    return binascii.hexlify(buf.getvalue()).decode("utf-8")


def _1_9(cls) -> str:
    return ""
