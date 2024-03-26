# -*- coding: utf-8 -*-

import random
import requests

from mainsail import cfg
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
            peer = random.choice(cfg.peers)
            if self.port not in peer["ports"]:
                peer = False
            n -= 1
        if peer is False:
            raise ApiError(
                f"no peer available with '{self.port}' port enabled"
            )
        return self.func(
            f"http://{peer['ip']}:{peer['ports'][self.port]}/{self.path}/"
            f"{'/'.join(path)}" + (f"?{urlencode(data)}" if len(data) else ""),
            headers=self.headers,
            json=data
        ).json()


# TODO: improve
def use_network(peer: str) -> None:
    cfg._clear()

    for key, value in requests.get(
        f"{peer}/api/node/configuration",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {}).items():
        cfg._track.append(key)
        setattr(cfg, key, value)

    get_peers(peer)
    cfg._track.append("peers")

    fees = requests.get(
        f"{peer}/api/node/fees?days=30",
        headers={'Content-type': 'application/json'},
    ).json().get("data", {})
    setattr(cfg, "fees", fees)
    cfg._track.append("fees")


def get_peers(peer: str, latency: int = 200) -> None:
    resp = sorted(
        requests.get(
            f"{peer}/api/peers", headers={'Content-type': 'application/json'}
        ).json().get("data", {}),
        key=lambda p: p["latency"]
    )
    setattr(cfg, "peers", [
        {
            "ip": peer["ip"],
            "ports": dict(
                [k.split("/")[-1], v] for k, v in peer["ports"].items()
                if v > 0
            )
        }
        for peer in resp if peer["latency"] <= latency
    ])


GET = EndPoint(port="api-development")
WHK = EndPoint(port="api-webhook")
POST = EndPoint(port="api-transaction-pool", func=requests.post)
WHKP = EndPoint(port="api-webhook", func=requests.post)
WHKD = EndPoint(port="api-webhook", func=requests.delete)
