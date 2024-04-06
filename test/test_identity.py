# -*- coding: utf-8 -*-

import os
from unittest import TestCase
from mainsail import identity, loadJson


class KeyRingTest(TestCase):

    def test_dump_and_load(self):
        krg = identity.KeyRing(int.from_bytes(os.urandom(32)))
        pin_code = [0, 0, 0, 0, 0, 0]
        krg.dump(pin_code)
        self.assertEqual(krg, identity.KeyRing.load(pin_code))

    def test_bip40_managment(self):
        self.assertEqual(
            getattr(identity.config, "bip340", False),
            isinstance(
                identity.KeyRing.create(int.from_bytes(os.urandom(32))),
                identity.Schnorr
            )
        )
        setattr(identity.config, "bip340", True)
        self.assertEqual(
            getattr(identity.config, "bip340", False),
            isinstance(
                identity.KeyRing.create(int.from_bytes(os.urandom(32))),
                identity.Schnorr
            )
        )


class DefinitionTest(TestCase):

    def test_bip39_hash(self):
        # vectors from https://github.com/trezor/python-mnemonic/tree/master
        vectors = loadJson(
            os.path.join(os.path.dirname(__file__), "bip39_hash.json")
        )
        for mnemonic, hash in vectors:
            self.assertEqual(
                identity.bip39_hash(mnemonic, passphrase="TREZOR").hex(),
                hash
            )

    def test_wallet_from_puk(self):
        setattr(identity.config, "version", 30)
        self.assertEqual(
            identity.get_wallet(
                "02968e862011738ac185e87f47dec61b32c842fd8e24fab625c02a15ad7e2"
                "d0f65"
            ), "D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv"
        )

    def test_puk_combination(self):
        pass
