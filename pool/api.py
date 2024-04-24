# -*- coding: utf-8 -*-

import os
import threading

from pool import tbw, flask, loadJson, main, app, JOB


@app.route("/<string:puk>", methods=["GET"])
def delegate(puk: str) -> flask.Response:
    info = loadJson(os.path.join(tbw.DATA, f"{puk}.json"))
    if len(info):
        info.pop("prk", False)
        return flask.jsonify(info)
    return flask.jsonify({"status": 404})


@app.route("/<string:puk>/forgery", methods=["GET"])
def forgery(puk: str) -> flask.Response:
    path = os.path.join(tbw.DATA, puk, "forgery.json")
    if os.path.exists(path):
        forgery = loadJson(path)
        forgery.pop("reward", False)
        for k in forgery:
            if k not in ["blocks", "contributions"]:
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
