# -*- coding: utf-8 -*-

import sys

_track = []


def _clear():
    for name in _track:
        delattr(sys.modules[__name__], name)
    _track.clear()
