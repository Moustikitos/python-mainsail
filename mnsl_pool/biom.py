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
from mainsail import identity, rest, webhook, dumpJson, loadJson
from typing import Union, List

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DELEGATE_PARAMETERS = {
    "share": float,
    "min_vote": float,
    "max_vote": float,
    "min_share": float,
    "excludes": list,
    "block_delay": int,
    "message": str,
    "chunck_size": int,
    "wallet": str
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
        elif key == "excludes":
            addresses = []
            for address in [
                addr.strip() for addr in value.split(",") if addr != ""
            ]:
                try:
                    base58.b58decode_check(address)
                except Exception:
                    LOGGER.info(f"{address} is not a valid wallet address")
                else:
                    addresses.append(address)
            params[key] = addresses
        elif key in DELEGATE_PARAMETERS.keys():
            try:
                params[key] = DELEGATE_PARAMETERS[key](value)
            except Exception:
                LOGGER.info(
                    f"conversion into {DELEGATE_PARAMETERS[key]} "
                    f"impossible for {value}"
                )
        else:
            params[key] = value
    LOGGER.info(f"grabed options: {params}")
    return params


def get_nonces():
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
    endpoint.headers = secure_headers(headers, prk)
    if data is None:
        return endpoint(peer=peer)
    else:
        return endpoint(data=data, peer=peer)


def deploy(host: str = "127.0.0.1", port: int = 5000):
    options = _merge_options()
    host = options.get("host", host)
    port = options.get("port", host)

    normpath = os.path.normpath
    executable = normpath(sys.executable)

    with io.open("./mnsl-srv.service", "w") as unit:
        unit.write(f"""[Unit]
Description=Mainsail TBW server
After=network.target

[Service]
User={os.environ.get('USER', 'unknown')}
WorkingDirectory={normpath(sys.prefix)}
Environment=PYTHONPATH={normpath(os.path.dirname(os.path.dirname(__file__)))}
ExecStart={os.path.dirname(executable)}/gunicorn 'pool.api:run(debug=False)' \
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
ExecStart={normpath(sys.executable)} -m pool --workers=1 --access-logfile -
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
    if not os.system("sudo systemctl restart mnsl-pool"):
        os.system("sudo systemctl start mnsl-pool")
    if not os.system("sudo systemctl restart mnsl-bg"):
        os.system("sudo systemctl start mnsl-bg")


def add_pool(**kwargs) -> None:
    options = _merge_options()
    puk = options.get("puk", None)
    if puk is None:
        raise IdentityError("no pulic key provided")
    # check identity
    prk = identity.KeyRing.create(kwargs.pop("prk", None))
    if prk.puk().encode() != puk:
        raise IdentityError(f"private key does not match public key {puk}")
    # secure private key using a pincode
    # it will give the possibility to mnsl-bg service to sign transactions
    answer = ""
    while re.match(r"^[0-9]+$", answer) is None:
        answer = getpass.getpass(
            "enter pin code to secure secret (only figures)> "
        )
    pincode = [int(e) for e in answer]
    prk.dump(pincode)
    # reach a network
    while not hasattr(rest.config, "nethash"):
        try:
            rest.use_network(
                input("provide a network peer API [default=localhost:4003]> ")
                or "http://127.0.0.1:4003"
            )
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            pass
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
    target_endpoint = None
    while target_endpoint is None:
        target_endpoint = input(
            "provide your target server [default=localhost:5000]> "
        ) or "http://127.0.0.1:5000"
        try:
            resp = requests.post(f"{target_endpoint}/block/forged", timeout=2)
            if resp.status_code not in [200, 403]:
                target_endpoint = None
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            target_endpoint = None
    # subscribe and save webhook id with other options
    ip, port = parse.urlparse(webhook_peer).netloc.split(":")
    options = _merge_options(
        **kwargs, prk=pincode, nethash=getattr(rest.config, "nethash"),
        webhook=webhook.subscribe(
            {"ip": ip, "ports": {"api-webhook": port}}, "block.forged",
            target_endpoint, webhook.condition(
                f"block.data.generatorPublicKey=={puk}"
            )
        )
    )
    # dump delegate options
    path = os.path.join(tbw.DATA, f"{puk}.json")
    dumpJson(dict(loadJson(path), **options), path, ensure_ascii=False)
    os.makedirs(os.path.join(tbw.DATA, puk), exist_ok=True)
    LOGGER.info(f"delegate {puk} set")


def set_pool(**kwargs) -> requests.Response:
    """
    ```bash
    $ set_pool ?key=value?
    ```

    *Pool parameters:*

    - [x] `share` - share rate in float number (0. <= share = 1.0).
    - [x] `min_vote` - minimum vote to be considered by the pool.
    - [x] `max_vote` - maximum vote weight caped in the pool.
    - [x] `min_share` - minimum reward to reach for a vote wallet to be
          included in payroll.
    - [x] `excludes` - comma-separated list of wallet to exclude.
    - [x] `block_delay` - number of forged block between two payrolls.
    - [x] `message` - vendorFied message to be set on each payroll transacion.
    - [x] `chunck_size` - maximum number of recipient for a multipayment.
    - [x] `wallet` - custom wallet to receive validator share.
    """
    # `peer` is just to be used inside this function so we pop it from kwargs
    # if # found there
    peer = kwargs.pop("peer", {})
    # merge kwargs with command line
    options = _merge_options(**kwargs)
    # because `ip` and `port` of remote pool can be set using command line args
    # we pop them from here
    if peer == {}:
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
