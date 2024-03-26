# -*- coding: utf-8 -*-

import io
import os
import json
import struct

from enum import IntEnum


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


def loadJson(path):
    """Load JSON data from path"""
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


def dumpJson(data, path):
    """Dump JSON data to path"""
    try:
        os.makedirs(os.path.dirname(path))
    except Exception:
        pass
    with io.open(path, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=4)
    try:
        out.close()
        del out
    except Exception:
        pass


def unpack(fmt, fileobj):
    # read value as binary data from buffer
    return struct.unpack(fmt, fileobj.read(struct.calcsize(fmt)))


def pack(fmt, fileobj, values):
    # write value as binary data into buffer
    return fileobj.write(struct.pack(fmt, *values))


def unpack_bytes(f, n):
    # read bytes from buffer
    return unpack("<%ss" % n, f)[0]


def pack_bytes(f, v):
    # write bytes into buffer
    return pack("<%ss" % len(v), f, (v,))
