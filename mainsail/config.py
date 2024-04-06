# -*- coding: utf-8 -*-

import os
import sys
import pickle

DATA = os.path.join(os.getenv("HOME"), ".mainsail", ".networks")
_track = []


def _clear():
    for name in _track:
        delattr(sys.modules[__name__], name)
    _track.clear()


def _dump():
    path = os.path.join(
        DATA, f"{getattr(sys.modules[__name__], 'network')}.net"
    )
    os.makedirs(DATA, exist_ok=True)
    with open(path, "wb") as output:
        pickle.dump(
            dict(
                [attr, getattr(sys.modules[__name__], attr)]
                for attr in _track
            ), output
        )


def _load(name):
    path = os.path.join(DATA, f"{name}.net")
    if os.path.exists(path):
        _clear()
        with open(path, "rb") as input:
            for attr, value in pickle.load(input).items():
                setattr(sys.modules[__name__], attr, value)
                _track.append(attr)
