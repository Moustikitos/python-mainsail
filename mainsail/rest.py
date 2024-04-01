# -*- coding: utf-8 -*-

import random
import requests

from mainsail import config
from urllib.parse import urlencode


class ApiError(Exception):
    pass


class EndPoint(object):

    def __init__(self, *path, **opt):
        self.headers = opt.pop("headers", {'Content-type': 'application/json'})
        self.port = opt.pop("port", "api-development")
        self.func = opt.pop("func", requests.get)
        self.path = "/".join(path)

    def __getattr__(self, attr):
        if attr not in object.__getattribute__(self, "__dict__"):
            if self.path == "":
                return EndPoint(
                    attr, headers=self.headers, func=self.func, port=self.port)
            else:
                return EndPoint(
                    self.path, attr, headers=self.headers, func=self.func,
                    port=self.port
                )
        else:
            return object.__getattribute__(self, attr)

    def __call__(self, *path, **data):
        peer, n = data.pop("peer", False), 10
        while peer is False and n >= 0:
            peer = random.choice(config.peers)
            ports = list(set(self.port) & set(peer["ports"].keys()))
            if not len(ports):
                peer = False
            n -= 1
        if peer is False:
            raise ApiError(
                f"no peer available with '{self.port}' port enabled"
            )
        return self.func(
            f"http://{peer['ip']}:{peer['ports'][ports[0]]}/{self.path}/"
            f"{'/'.join(path)}" + (f"?{urlencode(data)}" if len(data) else ""),
            headers=self.headers,
            json=data
        ).json()


# TODO: improve
def use_network(peer: str) -> None:
    config._clear()

    for key, value in requests.get(
        f"{peer}/api/node/configuration",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {}).items():
        config._track.append(key)
        setattr(config, key, value)

    get_peers(peer)
    config._track.append("peers")

    fees = requests.get(
        f"{peer}/api/node/fees?days=30",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {})
    setattr(config, "fees", fees)
    config._track.append("fees")


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


# api root endpoints
GET = EndPoint(port=["api-development", "api-http"])
# transaction pool root endpoint
POST = EndPoint(port=["api-transaction-pool"], func=requests.post)
# webhook root endpoints
WHK = EndPoint(port=["api-webhook"])
WHKP = EndPoint(port=["api-webhook"], func=requests.post)
WHKD = EndPoint(port=["api-webhook"], func=requests.delete)
