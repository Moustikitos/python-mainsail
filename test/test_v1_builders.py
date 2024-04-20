# -*- coding: utf-8 -*-

from cSecp256k1 import PublicKey
from unittest import TestCase
from mainsail import rest, identity
from mainsail.tx import v1

ONLINE = rest.load_network(
    "7b9a7c6a14d3f8fb3f47c434b8c6ef0843d5622f6c209ffeec5411aabbf4bf1c"
)
PASSPHRASE = "super secured passphrase"


def is_online(func):
    def wrapper(*args, **kw):
        if ONLINE:
            return func(*args, **kw)
        else:
            print(f"\nescaping function {func.__name__}")
    return wrapper


class BuilderTest(TestCase):

    @is_online
    def test_type_0(self) -> None:
        tx = v1.Transfer(1.0, "DB1M7oukX8q4b8NPMXyX1cpXpX6shRrQeD", "message")
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_2(self) -> None:
        tx = v1.ValidatorRegistration()
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_3(self) -> None:
        tx = v1.Vote("genesis_1")
        tx.upVote("genesis_2")
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_4(self) -> None:
        tx = v1.MultiSignature()
        tx.senderPublicKey = identity.user_keys(PASSPHRASE)["publicKey"]
        for secret in ["secret001", "secret002", "secret003"]:
            tx.addParticipant(PublicKey.from_secret(secret).encode())
        for secret in ["secret001", "secret002", "secret003"]:
            tx.multiSign(secret)
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_6(self) -> None:
        tx = v1.MultiPayment()
        for secret in ["secret001", "secret002", "secret003"]:
            tx.addPayment(
                1.0,
                identity.get_wallet(PublicKey.from_secret(secret).encode())
            )
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_7(self) -> None:
        tx = v1.ValidatorResignation()
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_8(self) -> None:
        tx = v1.UsernameRegistration("username")
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )

    @is_online
    def test_type_9(self) -> None:
        tx = v1.UsernameResignation()
        tx.sign(PASSPHRASE)
        resp = tx.send()
        self.assertEqual(len(resp["data"]["invalid"]), 1)
        self.assertIn(
            resp["errors"]["0"]["type"], ["ERR_OTHER", "ERR_LOW_FEE"]
        )
