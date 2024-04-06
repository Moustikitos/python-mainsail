# -*- coding: utf-8 -*-

from cSecp256k1 import PublicKey
from unittest import TestCase
from mainsail import rest, identity
from mainsail.tx import v1


def is_online(func):
    def wrapper(*args, **kw):
        if len(getattr(rest.config, "peers", [])):
            return func(*args, **kw)
        else:
            print(f"escaping function {func.__name__}")
    return wrapper


class BuilderTest(TestCase):

    def setUp(self) -> None:
        return super().setUp()

    def test_type_0(self) -> None:
        self.assertIsInstance(
            v1.Transfer(1.0, "DB1M7oukX8q4b8NPMXyX1cpXpX6shRrQeD", "message"),
            v1.Transfer
        )

    @is_online
    def test_type_2(self) -> None:
        tx = v1.ValidatorRegistration()
        tx.sign("12 word passphrase")
        self.assertIsInstance(tx, v1.ValidatorRegistration)

    @is_online
    def test_type_3(self) -> None:
        tx = v1.Vote()
        tx.upVote("username001")
        tx.upVote("username002")
        self.assertIsInstance(tx, v1.Vote)

    def test_type_4(self) -> None:
        tx = v1.MultiSignature()
        tx.addParticipant(PublicKey.from_secret("secret001").encode())
        tx.addParticipant(PublicKey.from_secret("secret002").encode())
        tx.addParticipant(PublicKey.from_secret("secret003").encode())
        self.assertIsInstance(tx, v1.MultiSignature)

    def test_type_6(self) -> None:
        tx = v1.MultiPayment()
        for secret in ["secret001", "secret002", "secret003"]:
            tx.addPayment(
                1.0,
                identity.get_wallet(PublicKey.from_secret(secret).encode())
            )
        self.assertIsInstance(tx, v1.MultiPayment)

    def test_type_7(self) -> None:
        self.assertIsInstance(
            v1.ValidatorResignation(),
            v1.ValidatorResignation
        )

    def test_type_8(self) -> None:
        self.assertIsInstance(
            v1.UsernameRegistration("username"),
            v1.UsernameRegistration
        )

    def test_type_9(self) -> None:
        self.assertIsInstance(
            v1.UsernameResignation(),
            v1.UsernameResignation
        )
