# -*- coding: utf-8 -*-

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
