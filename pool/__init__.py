# -*- coding: utf-8 -*-

"""
This package provides managment tools to run a pool on arkEcosystem mainsail
framework. It computes a true block weight (TBW) distribution of block reward
according to instant participant vote weight.

## Install on Ubuntu

```bash
wget https://bit.ly/3U6BI8v
bash mnsl-pool.sh
```

Setup script creates 7 commands into `~/.bash_aliases` file:

* [x] `mnsl_pool_deploy` takes broadcast ip address and port to create
  services managed by `systemd`.
* [x] `add_validator` takes a validator public key to configure listening
  subscription on blockchain.
* [x] `set_validator` modifies validator TBW service parameters.
* [x] `mnsl_venv_activate` activates the virtual environment used to run
  mainsail pool.
* [x] `restart_mnsl_pool` restarts the server.
* [x] `restart_mnsl_bg` restarts background tasks.
* [x] `log_mnsl_pool` shows server logs.
* [x] `log_mnsl_bg` shows background tasks logs.
"""

import os
import json
import queue
import flask
import logging

from mainsail import webhook, loadJson, dumpJson
from pool import tbw, biom

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

CONF_PARAMETERS = [
    "sleep_time"
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


@app.route("/configure", methods=["POST"])
def configure():
    if biom.check_headers(flask.request.headers):
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
    if biom.check_headers(flask.request.headers):
        puk = flask.request.headers["puk"]
        path = os.path.join(tbw.DATA, f"{puk}.json")
        data = json.loads(flask.request.data)
        info = dict(
            loadJson(path), **dict(
                [k, v] for k, v in data.items()
                if k in biom.DELEGATE_PARAMETERS.keys()
            )
        )
        if flask.request.method == "POST":
            LOGGER.debug(f"---- received> {data}")
            LOGGER.info(f"updating {puk} info> {info}")
            dumpJson(info, path, ensure_ascii=False)
            return flask.jsonify({"status": 204, "updated": data}), 204
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
                LOGGER.exception("#### error occured>")
            else:
                LOGGER.info("update forgery> %s", result)
            finally:
                biom.releaseLock(lock)
        elif block is False:
            break
    LOGGER.info("main loop exited")
