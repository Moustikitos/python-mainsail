# -*- coding: utf-8 -*-

import os
import sys
import binascii

from io import BytesIO
from mainsail import TYPES
from mainsail.transaction import Transaction

# sort all version modules and import all from the last one
v_modules = sorted(
    [
        n.replace(".py", "") for n in os.listdir(__path__[0])
        if n.startswith("v")
    ],
    key=lambda n: int(n[1:])
)
exec(f"from mainsail.tx.{v_modules[-1]} import *")


def deserialize(serial: str) -> Transaction:
    """
    Build a transaction from hexadecimal string.

    Args:
        serial (str): the serialized transaction as hexadecimal string.

    Returns:
        Transaction: the transaction.

    Raises:
        AttributeError: if transaction builder is not defined.
    """
    buf = BytesIO(binascii.unhexlify(serial))
    data = Transaction.deserializeCommon(buf)
    # transform TYPES enum name to class name
    name = "".join(e.capitalize() for e in TYPES(data["type"]).name.split("_"))
    # get transaction builder class
    try:
        tx = getattr(sys.modules[__name__], name)()
    except AttributeError:
        raise AttributeError(
            f"transaction type {TYPES(data['type']).value} builder "
            "is not defined"
        )
    for key, value in data.items():
        setattr(tx, key, value)
    tx.deserializeAsset(buf)
    tx.deserializeSignatures(buf)
    return tx
