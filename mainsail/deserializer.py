# -*- coding: utf-8 -*-

import base58
import binascii
from typing import TextIO
from mainsail import unpack, unpack_bytes


def _1_0(cls, buf: TextIO):
    cls.amount, cls.expiration = unpack("<QI", buf)
    recipientId = base58.b58encode_check(unpack_bytes(buf, 21))
    cls.recipientId = recipientId.decode("utf-8")


def _1_2(cls, buf: TextIO):
    cls.asset["validatorPublicKey"] = \
        binascii.hexlify(unpack_bytes(buf, 96)).decode("utf-8")


def _1_3(cls, buf: TextIO):
    n, = unpack("<B", buf)
    cls.asset["votes"] = [
        binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
        for i in range(n)
    ]
    n, = unpack("<B", buf)
    cls.asset["unvotes"] = [
        binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
        for i in range(n)
    ]


def _1_4(cls, buf: TextIO):
    cls.asset["multiSignature"]["min"], n = unpack("<BB", buf)
    cls.asset["multiSignature"]["publicKeys"] = [
        binascii.hexlify(unpack_bytes(buf, 33)).decode("utf-8")
        for i in range(n)
    ]


def _1_6(cls, buf: TextIO):
    n, = unpack("<H", buf)
    for i in range(n):
        amount, = unpack("<Q", buf)
        address, = base58.b58encode_check(unpack_bytes(buf, 21))
        cls.assets["payments"][i] = {
            "recipientId": address.decode("utf-8"), "amount": amount
        }


def _1_7(cls, buf: TextIO):
    pass


def _1_8(cls, buf: TextIO):
    n, = unpack("<B", buf)
    cls.asset = {"username": unpack_bytes(buf, n).decode("utf-8")}


def _1_9(cls, buf: TextIO):
    pass
