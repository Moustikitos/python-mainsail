# -*- coding: utf-8 -*-

import os
import threading
from mainsail import rest

from mnsl_pool import tbw, flask, loadJson, main, app, JOB


def _find(puk_or_username):
    if os.path.isfile(os.path.join(tbw.DATA, f"{puk_or_username}.json")):
        return puk_or_username
    for name in [n for n in os.listdir(tbw.DATA) if n.endswith(".json")]:
        try:
            rest.load_network(
                loadJson(os.path.join(tbw.DATA, name))["nethash"]
            )
        except Exception:
            pass
        else:
            puk = name.split(".")[0]
            attributes = rest.GET.api.wallets(puk).get("attributes", {})
            tbw.LOGGER.info(f"{name} : {attributes}")
            if puk_or_username == attributes.get("username", ""):
                return puk


@app.route("/<string:puk>", methods=["GET"])
def validator(puk: str) -> flask.Response:
    if puk.endswith(".ico"):
        return "", 404
    puk = _find(puk)
    info = loadJson(os.path.join(tbw.DATA, f"{puk}.json"))
    if len(info):
        info.pop("prk", False)
        return flask.jsonify(info)
    return flask.jsonify({"status": 404})


@app.route("/<string:puk>/forgery", methods=["GET"])
def forgery(puk: str) -> flask.Response:
    puk = _find(puk)
    path = os.path.join(tbw.DATA, puk, "forgery.json")
    if os.path.exists(path):
        forgery = loadJson(path)
        forgery.pop("reward", False)
        for k in forgery:
            if k not in ["blocks", "contributions", "lost XTOSHI"]:
                forgery[k] /= tbw.XTOSHI
        for k in forgery.get("contributions", {}):
            forgery["contributions"][k] /= tbw.XTOSHI
        return flask.jsonify(forgery)
    return flask.jsonify({"status": 404})


def run(debug: bool = True) -> flask.Flask:
    global app, MAIN

    MAIN = threading.Thread(target=main)
    MAIN.daemon = True
    MAIN.start()

    if debug:
        app.run("127.0.0.1", 5000)
        JOB.put(False)
    else:
        return app
