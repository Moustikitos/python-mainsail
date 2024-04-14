# -*- coding: utf-8 -*-

import io
import os
import json
import struct

from typing import TextIO, Union
from enum import IntEnum

XTOSHI = 1e8


class TYPES(IntEnum):
    TRANSFER = 0
    VALIDATOR_REGISTRATION = 2
    VOTE = 3
    MULTI_SIGNATURE = 4
    MULTI_PAYMENT = 6
    VALIDATOR_RESIGNATION = 7
    USERNAME_REGISTRATION = 8
    USERNAME_RESIGNATION = 9


class TYPE_GROUPS(IntEnum):
    TEST = 0
    CORE = 1
    RESERVED = 1000  # Everything above is available to anyone


class EXPIRATION_TYPES(IntEnum):
    EPOCH_TIMESTAMP = 1
    BLOCK_HEIGHT = 2


def loadJson(path: str) -> Union[dict, list]:
    "Load JSON data from path"
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8") as in_:
            data = json.load(in_)
    else:
        data = {}
    try:
        in_.close()
        del in_
    except Exception:
        pass
    return data


def dumpJson(data: Union[dict, list], path: str, **opt) -> None:
    "Dump JSON data to path"
    if "indent" not in opt:
        opt["indent"] = 4
    try:
        os.makedirs(os.path.dirname(path))
    except Exception:
        pass
    with io.open(path, "w", encoding="utf-8") as out:
        json.dump(data, out, **opt)
    try:
        out.close()
        del out
    except Exception:
        pass


def unpack(fmt: str, fileobj: TextIO) -> tuple:
    "Read value as binary data from buffer"
    return struct.unpack(fmt, fileobj.read(struct.calcsize(fmt)))


def pack(fmt: str, fileobj: TextIO, values: tuple):
    "Write values as binary data into buffer"
    return fileobj.write(struct.pack(fmt, *values))


def unpack_bytes(f: TextIO, n: int) -> bytes:
    "Read n bytes from buffer"
    return unpack("<%ss" % n, f)[0]


def pack_bytes(f: TextIO, v: bytes) -> int:
    "Write bytes into buffer"
    return pack("<%ss" % len(v), f, (v,))
