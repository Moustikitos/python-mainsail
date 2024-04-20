# -*- coding: utf-8 -*-

import os
import json
import queue
import flask
import logging

from mainsail import webhook, rest, identity, loadJson, dumpJson
from pool import tbw, biom
from typing import Union, List

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

CONF_PARAMETERS = [
    "sleep_time"
]

DELEGATE_PARAMETERS = [
    "share", "min_vote", "max_vote", "peer", "vendorField", "excludes",
    "block_delay", "message", "chunck_size", "peer"
]

# create worker and its queue
JOB = queue.Queue()

# create the application instance
app = flask.Flask(__name__)
app.config.update(
    # 300 seconds = 5 minutes lifetime session
    PERMANENT_SESSION_LIFETIME=300,
    # used to encrypt cookies
    # secret key is generated each time app is restarted
    SECRET_KEY=os.urandom(32),
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
        path = os.path.join(tbw.DATA, f"{headers['puk']}.json")
        if not os.path.exists(path):
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
) -> flask.Response:
    endpoint.headers = secure_headers(headers, prk)
    if data is None:
        return endpoint(peer=peer)
    else:
        return endpoint(data=data, peer=peer)


@app.route("/configure", methods=["POST"])
def configure():
    if check_headers(flask.request.headers):
        if flask.request.method == "POST":
            path = os.path.join(tbw.DATA, ".conf")
            data = json.loads(flask.request.data).get("data", {})
            conf = dict(
                loadJson(path), **dict(
                    [k, v] for k, v in data.items() if k in CONF_PARAMETERS
                )
            )
            dumpJson(conf, path, ensure_ascii=False)
            return flask.jsonify({"status": 204}), 204
    else:
        return flask.jsonify({"status": 403}), 403


@app.route("/configure/delegate/", methods=["POST", "GET"])
def configure_delegate() -> flask.Response:
    if check_headers(flask.request.headers):
        puk = flask.request.headers["puk"]
        path = os.path.join(tbw.DATA, f"{puk}.json")
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
def block_forged() -> flask.Response:
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
