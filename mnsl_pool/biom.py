# -*- coding: utf-8 -*-

import io
import os
import re
import sys
import math
import time
import base58
import getpass
import logging
import datetime
import requests

from datetime import timezone
from urllib import parse
from mnsl_pool import tbw
from mainsail import identity, rest, webhook
from typing import Union, List

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

POOL_PARAMETERS = {
    "share": float,
    "min_vote": float,
    "max_vote": float,
    "min_share": float,
    "excludes": list,
    "exclusives": list,
    "block_delay": int,
    "message": str,
    "chunck_size": int,
    "wallet": str,
    "api_peer": dict,
    "webhook": str,
    "nethash": str
}

try:
    import fcntl

    def acquireLock():
        '''acquire exclusive lock file access'''
        locked_file_descriptor = open(
            os.path.join(os.getenv("HOME"), '.lock'), 'w+'
        )
        LOGGER.info("acquiering global lock...")
        fcntl.flock(locked_file_descriptor, fcntl.LOCK_EX)
        return locked_file_descriptor

    def releaseLock(locked_file_descriptor):
        '''release exclusive lock file access'''
        fcntl.flock(locked_file_descriptor, fcntl.LOCK_UN)
        locked_file_descriptor.close()
        LOGGER.info("global lock released")

except ImportError:
    import msvcrt

    def acquireLock():
        '''acquire exclusive lock file access'''
        locked_file_descriptor = open(
            os.path.join(os.getenv("HOME"), '.lock'), 'w+'
        )
        locked_file_descriptor.seek(0)
        LOGGER.info("acquiering global lock...")
        while True:
            try:
                msvcrt.locking(
                    locked_file_descriptor.fileno(), msvcrt.LK_LOCK, 1
                )
            except OSError:
                pass
            else:
                break
        return locked_file_descriptor

    def releaseLock(locked_file_descriptor):
        '''release exclusive lock file access'''
        locked_file_descriptor.seek(0)
        msvcrt.locking(locked_file_descriptor.fileno(), msvcrt.LK_UNLCK, 1)
        LOGGER.info("global lock released")


class IdentityError(Exception):
    pass


def _merge_options(**options):
    # update from command line
    for arg in [a for a in sys.argv if "=" in a]:
        key, value = arg.split("=")
        key = key.replace("--", "").replace("-", "_")
        options[key] = value
    # manage parameters
    params = {}
    for key, value in options.items():
        if key == "api_peer":
            if isinstance(value, str):
                params[key] = rest.Peer(value)
            elif isinstance(value, dict):
                params[key] = value
        if key == "port":
            try:
                params[key] = int(value)
            except Exception:
                LOGGER.info(
                    f"conversion into {type(0)} impossible for {value}"
                )
        elif key == "wallet":
            try:
                base58.b58decode_check(value)
            except Exception:
                LOGGER.info(f"{value} is not a valid wallet address")
            else:
                params[key] = value
        # to accept excludes:[add|pop]=... and exclusives:[add|pop]=...
        elif "excludes" in key or "exclusives" in key:
            addresses = []
            if isinstance(value, str):
                value = [
                    addr.strip() for addr in value.split(",") if addr != ""
                ]
            for address in value:
                try:
                    base58.b58decode_check(address)
                except Exception:
                    LOGGER.info(f"{address} is not a valid wallet address")
                else:
                    addresses.append(address)
            params[key] = addresses
        elif key in POOL_PARAMETERS.keys():
            try:
                params[key] = POOL_PARAMETERS[key](value)
            except Exception:
                LOGGER.info(
                    f"conversion into {POOL_PARAMETERS[key]} "
                    f"impossible for {value}"
                )
        else:
            params[key] = value
    LOGGER.info(f"grabed options: {params}")
    return params


def get_nonces():
    # computes two consecutive timed nonce
    base_time = math.ceil(time.time()/5) * 5
    datetimes = [
        datetime.datetime.fromtimestamp(base_time + n)
        .astimezone(timezone.utc).strftime("%Y-%m-%H%m%S").encode("utf-8")
        for n in [-5, 0]
    ]
    return [
        identity.cSecp256k1.hash_sha256(dt).decode("utf-8")
        for dt in datetimes
    ]


def secure_headers(
    headers: dict = {},
    prk: Union[identity.KeyRing, List[int], str, int] = None
) -> dict:
    if isinstance(prk, list):
        prk = identity.KeyRing.load(prk)
    elif not isinstance(prk, identity.KeyRing):
        prk = identity.KeyRing.create(prk)
    nonce = get_nonces()[-1]
    headers.update(
        nonce=nonce,
        sig=prk.sign(nonce).raw(),
        puk=prk.puk().encode()
    )
    return headers


def check_headers(headers: dict) -> bool:
    try:
        path = os.path.join(tbw.DATA, f"{headers['puk']}")
        valid_nonces = get_nonces()
        LOGGER.debug(
            f"---- received nonce {headers['nonce']} - "
            f"valid nonces: {'|'.join(valid_nonces)}"
        )
        if os.path.isdir(path) and headers["nonce"] in valid_nonces:
            return identity.get_signer().verify(
                headers["puk"], headers["nonce"], headers["sig"]
            )
    except KeyError:
        pass
    return False


def secured_request(
    endpoint: rest.EndPoint, data: dict = None,
    prk: Union[identity.KeyRing, List[int], str, int] = None,
    headers: dict = {}, peer: dict = None
) -> requests.Response:
    if data is None:
        return endpoint(
            peer=peer, headers=secure_headers(headers or endpoint.headers, prk)
        )
    else:
        return endpoint(
            data=data, peer=peer,
            headers=secure_headers(headers or endpoint.headers, prk)
        )


def deploy(host: str = "127.0.0.1", port: int = 5000):
    """
    **Deploy pool server**

    ```python
    >>> from mnsl_pool import biom
    >>> biom.deploy()
    ```

    ```bash
    ~$ mnsl_deploy # use ip address 0.0.0.0 with port #5000
    ```

    If you plan to deploy pool server behind a proxy, it is possible to
    using `host` and `port` parameters:

    ```python
    >>> from mnsl_pool import biom
    >>> biom.deploy(host="127.0.0.1", port=7542)
    ```

    ```bash
    ~$ mnsl_deploy host=127.0.0.1 port=7542 # use localhost address with port \
#7542
    ```
    """
    options = _merge_options()
    host = options.get("host", host)
    port = options.get("port", port)

    normpath = os.path.normpath
    executable = normpath(sys.executable)

    with io.open("./mnsl-srv.service", "w") as unit:
        unit.write(f"""[Unit]
Description=Mainsail TBW server
After=network.target

[Service]
User={os.environ.get('USER', 'unknown')}
WorkingDirectory={normpath(sys.prefix)}
ExecStart={os.path.dirname(executable)}/gunicorn \
'mnsl_pool.api:run(debug=False)' \
--bind={host}:{port} --workers=2 --timeout 10 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
""")

    with io.open("./mnsl-bg.service", "w") as unit:
        unit.write(f"""[Unit]
Description=Mainsail pool backround tasks
After=network.target

[Service]
User={os.environ.get("USER", "unknown")}
WorkingDirectory={normpath(sys.prefix)}
Environment=PYTHONPATH={normpath(os.path.dirname(os.path.dirname(__file__)))}
ExecStart={normpath(sys.executable)} -m mnsl_pool \
--workers=1 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
""")

    if os.system(f"{executable} -m pip show gunicorn") != "0":
        os.system(f"{executable} -m pip install gunicorn")

    os.system("chmod +x ./mnsl-srv.service")
    os.system("chmod +x ./mnsl-bg.service")
    os.system("sudo mv --force ./mnsl-srv.service /etc/systemd/system")
    os.system("sudo mv --force ./mnsl-bg.service /etc/systemd/system")

    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart mnsl-srv"):
        os.system("sudo systemctl start mnsl-srv")
    if not os.system("sudo systemctl restart mnsl-bg"):
        os.system("sudo systemctl start mnsl-bg")


def dump_prk(
    prk: Union[identity.KeyRing, List[int], str, int] = None
) -> List[int]:
    # secure private key using a pincode
    if prk is None:
        prk = identity.KeyRing.create()
    answer = ""
    while re.match(r"^[0-9]+$", answer) is None:
        answer = getpass.getpass(
            "enter pin code to secure secret (only figures)> "
        )
    pincode = [int(e) for e in answer]
    prk.dump(pincode)
    return pincode


def add_pool(**kwargs) -> None:
    """
    **Initialize a pool**

    ```python
    >>> from mnsl_pool import biom
    >>> biom.add_pool(puk="033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec\
9c504db")
    ```

    ```bash
    ~$ add_pool puk=033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504db\
ba5477ba
    ```

    ```raw
    INFO:mnsl_pool.biom:grabed options: {'puk': '033f786d4875bcae61eb934e6af74\
090f254d7a0c955263d1ec9c504dbba5477ba'}
    Type or paste your passphrase >
    enter pin code to secure secret (only figures)>
    provide a network peer API [default=localhost:4003]>
    provide your webhook peer [default=localhost:4004]>
    provide your target server [default=localhost:5000]>
    INFO:mnsl_pool.biom:grabed options: {'prk': [0, 0, 0, 0], 'nethash': '7b9a\
7c6a14d3f8fb3f47c434b8c6ef0843d5622f6c209ffeec5411aabbf4bf1c', 'webhook': '47f\
4ede0-1dcb-4653-b9a2-20e766fc31d5', 'puk': '033f786d4875bcae61eb934e6af74090f2\
54d7a0c955263d1ec9c504dbba5477ba'}
    INFO:mnsl_pool.biom:delegate 033f786d4875bcae61eb934e6af74090f254d7a0c9552\
63d1ec9c504dbba5477ba set
    ```

    Check your pool using two endpoints:

    ```raw
    http://{ip}:{port}/{puk or username}
    http://{ip}:{port}/{puk or username}/forgery
    ```

    Pool data are stored in `~/.mainsail` folder.
    """
    options = _merge_options(**kwargs)
    puk = options.get("puk", None)
    if puk is None:
        raise IdentityError("no pulic key provided")
    # check identity
    prk = identity.KeyRing.create(kwargs.pop("prk", None))
    if prk.puk().encode() != puk:
        raise IdentityError(f"private key does not match public key {puk}")
    # dump the private key so mnsl-bg service can sign transactions
    pincode = dump_prk(prk)
    # reach a network
    api_peer = None
    while not hasattr(rest.config, "nethash"):
        try:
            api_peer = input(
                "provide a network peer API [default=localhost:4003]> "
            ) or "http://127.0.0.1:4003"
            rest.use_network(api_peer)
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            pass
    options["api_peer"] = rest.Peer(api_peer)
    options["username"] = rest.GET.api.wallets(puk).get("username", None)
    # reach a valid subscription node
    webhook_peer = None
    while webhook_peer is None:
        webhook_peer = input(
            "provide your webhook peer [default=localhost:4004]> "
        ) or "http://127.0.0.1:4004"
        try:
            resp = requests.head(f"{webhook_peer}/api/webhooks", timeout=2)
            if resp.status_code != 200:
                webhook_peer = None
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            webhook_peer = None
    # reach a valid target endpoint
    target_peer = None
    while target_peer is None:
        target_peer = input(
            "provide your target server [default=localhost:5000]> "
        ) or "http://127.0.0.1:5000"
        try:
            resp = requests.post(f"{target_peer}/block/forged", timeout=2)
            if resp.status_code not in [200, 403]:
                target_peer = None
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            target_peer = None
    # subscribe and save webhook id with other options
    ip, port = parse.urlparse(webhook_peer).netloc.split(":")
    options.update(
        prk=pincode, nethash=getattr(rest.config, "nethash"),
        webhook=webhook.subscribe(
            {"ip": ip, "ports": {"api-webhook": port}}, "block.forged",
            f"{target_peer}/block/forged", webhook.condition(
                f"generatorPublicKey=={puk}"
            )
        )
    )
    LOGGER.debug("data to be set as pool configuration> %s", options)
    resp = rest.POST.pool.configure(
        peer=rest.Peer(target_peer), **options,
        headers=secure_headers(rest.POST.headers, pincode)
    )
    if resp.get("status", None) == 204:
        LOGGER.info(f"{puk} pool added")
    return resp


def set_pool(**kwargs) -> requests.Response:
    """
    **Configure a pool**

    ```python
    >>> from mnsl_pool import biom
    >>> addresses = [
    ... "D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv",
    ... "DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU"
    ... ]
    >>> biom.set_pool(share=0.7, min_vote=10.0, exlusives=addresses)
    ```

    ```bash
    $ set_pool --share=0.7 --min-vote=10.0 --exclusives=D5Ha4o3UTuTd59vjDw1F26\
mYhaRdXh7YPv,DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU
    ```

    ```raw
    INFO:pool.biom:grabed options: {'share': 0.7, 'min_vote': 10.0, 'exclusive\
s': 'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv,DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU'}
    enter validator security pincode>
    {'status': 204, 'updated': {'exclusives': ['D5Ha4o3UTuTd59vjDw1F26mYhaRdXh\
7YPv', 'DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU'], 'min_vote': 10.0, 'share': 0.7}}
    ```

    Available pool parameters:

    - [x] `share` - share rate in float number (0. <= share = 1.0).
    - [x] `min_vote` - minimum vote to be considered by the pool.
    - [x] `max_vote` - maximum vote weight caped in the pool.
    - [x] `min_share` - minimum reward to reach for a vote wallet to be
          included in payroll.
    - [x] `excludes` - comma-separated list of wallet to exclude.
    - [x] `exclusives` - comma-separated list of private pool wallets.
    - [x] `block_delay` - number of forged block between two payrolls.
    - [x] `message` - vendorFied message to be set on each payroll transacion.
    - [x] `chunck_size` - maximum number of recipient for a multipayment.
    - [x] `wallet` - custom wallet to receive validator share.

    Available extra parameters:

    - [x] `url` - the url of node if domain name is set
    - [x] `ip` - the ip address of pool service
    - [x] `port` - the port used by pool service

    Those parameters are used to remotly configure pool options. Validator
    private key have to be secrured on the remote system using `dump_prk`. If
    no extra parameters are used, command will send request to
    `localhost:5000`.

    **Run a public pool**

    Voter selection can be donne using `min_vote` and `max_vote` options. A
    more convenient way is possible with `excludes` list, any address in this
    list wil be ignored by the TBW process.

    **Run a private pool**

    `min_vote` and `max_vote` parameters shouldn't be set but all the addresses
    granted by the private pool have to be mentioned in `exclusive` list.

    **`excludes` & `exclusives` lists**

    List parameters accept a custom action to add or remove item from list.

    ```bash
    (excludes|exclusives)[:add|:pop]=coma,separated,list,of,valid,addresses
    ```

    *Define a complete `exclusives` list:*

    ```bash
    $ set_pool exclusives=D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv,DTGgFwrVGf5JpvkMS\
p8QR5seEJ6tCAWFyU
    ```

    *Add `DCzk4aCBCeHTDUZ3RnkiK8aqpYYZ9iC51W` into `exclusives` list:*

    ```bash
    $ set_pool exclusives:add=DCzk4aCBCeHTDUZ3RnkiK8aqpYYZ9iC51W
    ```

    *Remove `D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv` from `exclusives` list:*

    ```bash
    $ set_pool exclusives:pop=D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv
    ```
    """
    # `peer` is just to be used inside this function so we pop it from kwargs
    # if found there
    peer = kwargs.pop("peer", {})
    # merge kwargs with command line
    options = _merge_options(**kwargs)
    # because `ip`, `port` or `url` of remote pool can be set using command
    # line args we pop them from here
    if peer == {}:
        if "url" in options:
            peer["url"] = options.pop("url")
            options.pop("ip", False)
            options.pop("port", False)
        else:
            peer["ip"] = options.pop("ip", "127.0.0.1")
            peer["ports"] = {"requests": options.pop("port", 5000)}
    # ask pincode if no one is given
    answer = options.pop("pincode", "")
    if "pincode" not in options:
        while re.match(r"^[0-9]+$", answer) is None:
            answer = getpass.getpass("enter validator security pincode> ")
    pincode = [int(e) for e in answer]
    # only valid delegate parameters available in `options` from there
    # secure POST headers and send parameters
    return rest.POST.pool.configure(
        peer=peer, **options,
        headers=secure_headers(rest.POST.headers, pincode)
    )
