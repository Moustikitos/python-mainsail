# -*- coding: utf-8 -*-
"""
Network endpoint managment module.
"""

import re
import requests

from typing import Union
from mainsail import config
from urllib.parse import urlencode, urlparse, urlunparse
from collections import namedtuple

# namedtuple to match the internal signature of urlunparse
Urltuple = namedtuple(
    typename='Urltuple', field_names=[
        'scheme', 'netloc', 'path', 'params', 'query', 'fragment'
    ]
)


class ApiError(Exception):
    pass


class Peer(dict):

    ip_port = r'([0-9]+(?:\.[0-9]+){3})(:[0-9]+)?'

    def __init__(
        self, url: str = "http://127.0.0.1", port_name: str = "requests"
    ) -> None:
        self.base_url = urlparse(url)
        test = re.match(Peer.ip_port, self.base_url.netloc)
        if test is not None:
            ip, port = test.groups()
            self["ip"] = ip
            if port is not None:
                self["ports"] = {port_name: int(port.replace(":", ""))}
        else:
            self["url"] = urlunparse(
                self.base_url._replace(
                    path="", params="", query="", fragment=""
                )
            )


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
        headers = data.pop("headers", self.headers)
        peer = data.pop("peer", False)
        n = len(getattr(config, "peers", []))
        ports = set([])  # void set
        # tries to fetch a valid peer
        while peer is False and n >= 0:
            # pot peer from available network peers and put it in the end
            peer = config.peers.pop(0)
            config.peers.append(peer)
            # match attended ports and enabled ports
            ports = set(self.ports) & set(peer.get("ports", {}).keys())
            peer = False if not len(ports) else peer
            n -= 1
        # if unsuccessful
        if peer is False:
            raise ApiError(
                f"no peer available with '{self.ports}' port enabled"
            )
        # else do HTTP request call
        # build an Urltuple to be updated according to needs
        if "url" in peer:
            base_url = urlparse(peer["url"])
        else:
            peer_ports = peer.get("ports", {})
            # if peer == {} return the a default base_url
            # default -> ["requests"]
            ports = list(
                ports or set(self.ports) & set(peer_ports.keys())
            ) or ["requests"]
            # default -> http://127.0.0.1:5000
            base_url = Urltuple(
                'http',
                f"{peer.get('ip', '127.0.0.1')}:" +
                f"{peer_ports.get(ports[0], 5000)}",
                None, None, None, None
            )
        base_url = base_url._replace(path='/'.join((self.path,) + path))
        if self.func in (requests.post, requests.delete):
            resp = self.func(urlunparse(base_url), headers=headers, json=data)
        else:
            base_url = base_url._replace(query=urlencode(data))
            resp = self.func(urlunparse(base_url), headers=headers)

        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError:
            return resp


def use_network(peer: str) -> None:
    config._clear()
    base_url = urlparse(peer)

    for key, value in requests.get(
        urlunparse(base_url._replace(path="api/node/configuration")),
        headers={'Content-type': 'application/json'},
    ).json().get("data", {}).items():
        setattr(config, key, value)
        config._track.append(key)

    fees = requests.get(
        urlunparse(base_url._replace(path="api/node/fees", query="days=30")),
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


def get_peers(peer: str, latency: int = 500) -> None:
    base_url = urlparse(peer)
    resp = sorted(
        requests.get(
            urlunparse(base_url._replace(path="api/peers")),
            headers={'Content-type': 'application/json'}
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
GET = EndPoint(ports=["api-http", "api-development", "core-api"])
# transaction pool root endpoint
POST = EndPoint(ports=["api-transaction-pool", "core-api"], func=requests.post)
# webhook root endpoints
WHK = EndPoint(ports=["api-webhook", "core-webhooks"])
WHKP = EndPoint(ports=["api-webhook", "core-webhooks"], func=requests.post)
WHKD = EndPoint(ports=["api-webhook", "core-webhooks"], func=requests.delete)
