# -*- coding: utf-8 -*-
"""
Network endpoint managment module.
"""

import random
import requests

from typing import Union
from mainsail import config
from urllib.parse import urlencode


class ApiError(Exception):
    pass


class EndPoint(object):

    def __init__(self, *path, **opt) -> None:
        self.headers = opt.pop("headers", {'Content-type': 'application/json'})
        self.ports = opt.pop("ports", "api-development")
        self.func = opt.pop("func", requests.get)
        self.path = "/".join(path)

    def __getattr__(self, attr: str) -> object:
        if attr not in object.__getattribute__(self, "__dict__"):
            if self.path == "":
                return EndPoint(
                    attr, headers=self.headers, func=self.func,
                    ports=self.ports
                )
            else:
                return EndPoint(
                    self.path, attr, headers=self.headers, func=self.func,
                    ports=self.ports
                )
        else:
            return object.__getattribute__(self, attr)

    def __call__(self, *path, **data) -> Union[list, dict, requests.Response]:
        peer, n = data.pop("peer", False), 10
        # n tries to fetch a valid peer
        while peer is False and n >= 0:
            # get a random peer from available network peers
            peer = random.choice(config.peers)
            # match attended ports and enabled ports
            peer = \
                False if not len(set(self.ports) & set(peer["ports"].keys())) \
                else peer
            n -= 1
        # if n unsuccessful tries
        if peer is False:
            raise ApiError(
                f"no peer available with '{self.ports}' port enabled"
            )
        # else do HTTP request call
        ports = list(set(self.ports) & set(peer["ports"].keys()))
        resp = self.func(
            f"http://{peer['ip']}:{peer['ports'][ports[0]]}/{self.path}/"
            f"{'/'.join(path)}" + (f"?{urlencode(data)}" if len(data) else ""),
            headers=self.headers,
            json=data
        )
        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError:
            return resp


def use_network(peer: str) -> None:
    config._clear()

    for key, value in requests.get(
        f"{peer}/api/node/configuration",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {}).items():
        setattr(config, key, value)
        config._track.append(key)

    fees = requests.get(
        f"{peer}/api/node/fees?days=30",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {})
    setattr(config, "fees", fees)
    config._track.append("fees")

    get_peers(peer)

    nethash = getattr(config, "nethash", False)
    if nethash:
        config._dump(nethash)


def load_network(name: str) -> bool:
    return config._load(name)


def get_peers(peer: str, latency: int = 200) -> None:
    resp = sorted(
        requests.get(
            f"{peer}/api/peers", headers={'Content-type': 'application/json'}
        ).json().get("data", {}),
        key=lambda p: p["latency"]
    )
    setattr(config, "peers", [
        {
            "ip": peer["ip"],
            "ports": dict(
                [k.split("/")[-1], v] for k, v in peer["ports"].items()
                if v > 0
            )
        }
        for peer in resp if peer["latency"] <= latency
    ])
    if "peers" not in config._track:
        config._track.append("peers")


# api root endpoints
GET = EndPoint(ports=["api-development", "api-http", "core-api"])
# transaction pool root endpoint
POST = EndPoint(ports=["api-transaction-pool", "core-api"], func=requests.post)
# webhook root endpoints
WHK = EndPoint(ports=["api-webhook", "core-webhooks"])
WHKP = EndPoint(ports=["api-webhook", "core-webhooks"], func=requests.post)
WHKD = EndPoint(ports=["api-webhook", "core-webhooks"], func=requests.delete)
