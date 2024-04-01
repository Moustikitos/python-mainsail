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
