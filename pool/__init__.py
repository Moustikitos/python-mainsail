# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import queue
import flask
import logging
import threading

from mainsail import webhook, rest, identity, loadJson, dumpJson
from pool import tbw, biom
from typing import Union, List

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DELEGATE_PARAMETERS = [
    "share", "min_vote", "max_vote", "peer", "vendorField", "excludes",
    "block_delay", "message", "chunck_size"
]

# create worker and its queue
JOB = queue.Queue()
PAYROLL = queue.Queue()

# create the application instance
app = flask.Flask(__name__)
app.config.update(
    # 300 seconds = 5 minutes lifetime session
    PERMANENT_SESSION_LIFETIME=300,
    # used to encrypt cookies
    # secret key is generated each time app is restarted
    SECRET_KEY=os.urandom(24),
    # JS can't access cookies
    SESSION_COOKIE_HTTPONLY=True,
    # if use of https
    SESSION_COOKIE_SECURE=False,
    # update cookies on each request
    # cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
    SESSION_REFRESH_EACH_REQUEST=True,
    #
    TEMPLATES_AUTO_RELOAD=True
)


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
        return identity.get_signer().verify(
            headers["puk"], headers["nonce"], headers["sig"]
        )
    except KeyError:
        return False


def secured_request(
    endpoint: rest.EndPoint, data: dict = None,
    prk: Union[identity.KeyRing, List[int], str, int] = None,
    headers: dict = {}, peer: dict = None
) -> flask.Response:
    endpoint.headers = secure_headers(headers, prk)
    if data is None:
        return endpoint(peer=peer)
    else:
        return endpoint(data=data, peer=peer)


@app.route("/configure/payroll", methods=["POST"])
def configure_tasks():
    if check_headers(flask.request.headers):
        if flask.request.method == "POST":
            data = json.loads(flask.request.data).get("data", {})
            PAYROLL.put(int(data["delay"]))
            return flask.jsonify({"status": 204}), 204
    else:
        return flask.jsonify({"status": 403}), 403


@app.route("/configure/delegate/", methods=["POST", "GET"])
def manage_delegate() -> flask.Response:
    if check_headers(flask.request.headers):
        puk = flask.request.headers["puk"]
        path = os.path.join(tbw.DATA, f"{puk}.json")
        if not os.path.exists(path):
            return flask.jsonify({"status": 404}), 404
        data = json.loads(flask.request.data).get("data", {})
        info = dict(
            loadJson(path), **dict(
                [k, v] for k, v in data.items() if k in DELEGATE_PARAMETERS
            )
        )
        if flask.request.method == "POST":
            LOGGER.debug(f"--- received> {data}")
            LOGGER.info(f"updating {puk} info> {info}")
            dumpJson(info, path, ensure_ascii=False)
            return flask.jsonify({"status": 204}), 204
        else:
            info.pop("prk", None)
            return flask.jsonify(info), 200
    else:
        return flask.jsonify({"status": 403}), 403


@app.route("/block/forged", methods=["POST", "GET"])
def manage_blocks() -> flask.Response:
    check = False
    if flask.request.method == "POST":
        check = webhook.verify(
            flask.request.headers.get("Authorization", "")[:32]
        )
        LOGGER.info("webhook check> %s", check)
        if check is True and flask.request.data != b'':
            data = json.loads(flask.request.data)
            block = data.get("data", {}).get("block", {}).get("data", {})
            LOGGER.debug("block received> %s", block)
            JOB.put(block)
        else:
            check = False
    return flask.jsonify({"acknowledge": check}), 200 if check else 403


def main():
    LOGGER.info("entering main loop")
    while True:
        block = JOB.get()
        if block not in [False, None]:
            lock = biom.acquireLock()
            try:
                result = tbw.update_forgery(block)
            except Exception:
                LOGGER.exception("---- error occured>")
            else:
                LOGGER.info("update forgery> %s", result)
            finally:
                biom.releaseLock(lock)
        elif block is False:
            break
    LOGGER.info("main loop exited")


def payroll():
    LOGGER.info("entering payroll loop")
    while True:
        delay = PAYROLL.get()
        if delay in [False, None]:
            break
        elif isinstance(delay, int):
            if PAYROLL.qsize() == 0:
                PAYROLL.put(delay)
            time.sleep(delay)
            LOGGER.info("sleep time finished, checking forgery...")
            for filename in [
                name for name in os.listdir(tbw.DATA)
                if name.endswith(".json")
            ]:
                puk = filename.split(".")[0]
                info = loadJson(os.path.join(tbw.DATA, filename))
                forgery = loadJson(os.path.join(tbw.DATA, puk, "forgery.json"))
                blocks = forgery.get("blocks", 0)
                block_delay = info.get("block_delay", 1000)
                if blocks > block_delay:
                    lock = biom.acquireLock()
                    try:
                        tbw.freeze_forgery(puk)
                    except Exception:
                        LOGGER.exception("---- error occured>")
                    else:
                        LOGGER.info(f"{puk} forgery frozen")
                    finally:
                        biom.releaseLock(lock)
                    tbw.bake_registry(puk)
                    for registry in [
                        reg for reg in os.listdir(os.path.join(tbw.DATA, puk))
                        if reg.endswith(".registry")
                    ]:
                        tx = loadJson(os.path.join(tbw.DATA, puk, registry))
                        LOGGER.info(
                            rest.POST.api("transaction-pool", transactions=tx)
                        )
    LOGGER.info("payroll loop exited")


def run(debug: bool = True):
    global app
    if debug:
        app.run("127.0.0.1", 5000)
        JOB.put(False)
        sys.exit(1)
    else:
        return app


MAIN = threading.Thread(target=main)
MAIN.daemon = True
MAIN.start()

THREAD1 = threading.Thread(target=payroll)
THREAD1.daemon = True
THREAD1.start()
