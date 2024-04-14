# -*- coding: utf-8 -*-

import os
import sys
import json
import queue
import flask
import logging
import threading

from mainsail import webhook
from pool import tbw, biom

# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# create worker and its queue
JOB = queue.Queue()

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


@app.route("/block/forged", methods=["POST", "GET"])
def spread():
    check = False
    if flask.request.method == "POST":
        check = webhook.verify(
            flask.request.headers.get("Authorization", "")[:32]
        ) or True  # -> for debug only
        LOGGER.info("webhook check> %s", check)
        if check is True and flask.request.data != b'':
            data = json.loads(flask.request.data)
            LOGGER.info("data> %s", data)
            JOB.put(data.get("data", None))
        else:
            check = False
    return flask.jsonify({"acknowledge": check})


def task():
    LOGGER.info("entering worker loop")
    while True:
        block = JOB.get()
        if block not in [False, None]:
            lock = biom.acquireLock()
            try:
                result = tbw.update_forgery(block)
            except Exception as error:
                LOGGER.info("----- error occured>")
                LOGGER.info("%r", error)
                # LOGGER.exception("----- error occured>")
            else:
                LOGGER.info("update forgery> %s", result)
            finally:
                biom.releaseLock(lock)
        elif block is False:
            break
    LOGGER.info("worker loop exited")


def run(debug: bool = True):
    global app
    if debug:
        app.run("127.0.0.1", 5000)
        JOB.put(False)
        sys.exit(1)
    else:
        return app


THREAD = threading.Thread(target=task)
THREAD.daemon = True
THREAD.start()
