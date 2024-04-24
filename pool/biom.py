# -*- coding: utf-8 -*-

import io
import os
import re
import sys
import base58
import getpass
import logging
import requests

from urllib import parse
from pool import tbw
from mainsail import identity, rest, webhook, dumpJson, loadJson
from typing import Union, List

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

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


def secure_headers(
    headers: dict = {},
    prk: Union[identity.KeyRing, List[int], str, int] = None
) -> dict:
    if isinstance(prk, list):
        prk = identity.KeyRing.load(prk)
    elif not isinstance(prk, identity.KeyRing):
        prk = identity.KeyRing.create(prk)
    nonce = os.urandom(64).hex()
    headers.update(
        nonce=nonce,
        sig=prk.sign(nonce).raw(),
        puk=prk.puk().encode()
    )
    return headers


def check_headers(headers: dict) -> bool:
    try:
        path = os.path.join(tbw.DATA, f"{headers['puk']}.json")
        if os.path.exists(path):
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
    normpath = os.path.normpath
    executable = normpath(sys.executable)

    with io.open("./mnsl-pool.service", "w") as unit:
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

    os.system("chmod +x ./mnsl-pool.service")
    os.system("chmod +x ./mnsl-bg.service")
    os.system("sudo mv --force ./mnsl-pool.service /etc/systemd/system")
    os.system("sudo mv --force ./mnsl-bg.service /etc/systemd/system")

    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart mnsl-pool"):
        os.system("sudo systemctl start mnsl-pool")
    if not os.system("sudo systemctl restart mnsl-bg"):
        os.system("sudo systemctl start mnsl-bg")


def _merge_options(**options):
    # update from command line
    for arg in [a for a in sys.argv if "=" in a]:
        key, value = arg.split("=")
        key = key.replace("--", "").replace("-", "_")
        options[key] = value
    # manage parameters
    params = {}
    for key, value in options.items():
        if key == "wallet":
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
    LOGGER.info(f"grabed options: {params}")
    return params


def add_delegate(puk: str, **kwargs) -> None:
    # check identity
    prk = identity.KeyRing.create()
    if prk.puk().encode() != puk:
        raise IdentityError(f"private key does not match public key {puk}")
    # save private key
    answer = ""
    while re.match(r"^[0-9]+$", answer) is None:
        answer = getpass.getpass("enter pin code to secure secret> ")
    pincode = [int(e) for e in answer]
    prk.dump(pincode)
    # reach a network
    while not hasattr(rest.config, "nethash"):
        try:
            rest.use_network(input("provide a valid network peer> "))
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as error:
            LOGGER.info("%r", error)
            pass
    # reach a valid subscription node
    webhook_peer = None
    while webhook_peer is None:
        webhook_peer = input("provide a valid webhook peer> ") \
            or "http://127.0.0.1:4004"
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
        target_endpoint = input("provide a valid target server> ") \
            or "http://127.0.0.1:5000"
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
    dumpJson(dict(options, **loadJson(path)), path, ensure_ascii=False)
    os.makedirs(os.path.join(tbw.DATA, puk), exist_ok=True)
    LOGGER.info(f"delegate {puk} set")


def set_delegate(**kwargs) -> requests.Response:
    # update from command line
    peer = kwargs.pop("peer", {})
    options = _merge_options(**kwargs)
    # asc pincode if no one is given
    if "pincode" not in options:
        answer = ""
        while re.match(r"^[0-9]+$", answer) is None:
            answer = getpass.getpass("enter validator secret pincode> ")
    pincode = [int(e) for e in options.pop("pincode", answer)]
    # secure POST headers and send parameters
    return rest.POST.configure.delegate(
        peer=peer, **options,
        headers=secure_headers(rest.POST.headers, pincode)
    )
