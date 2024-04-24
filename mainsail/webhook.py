# -*- coding: utf-8 -*-

import io
import os
import re
import pickle
import logging
import hashlib

from mainsail import rest, dumpJson, loadJson

DATA = os.path.join(os.getenv("HOME"), ".mainsail", ".webhooks")
REGEXP = re.compile(r'^([\w\.]*)\s*([^\w\s\^]*)\s*(.*)\s*$')
OPERATORS = {
    "<": "lt", "<=": "lte",
    ">": "gt", ">=": "gte",
    "==": "eq", "!=": "ne",
    "?": "truthy", "!?": "falsy",
    "\\": "regexp", "$": "contains",
    "<>": "between", "!<>": "not-between"
}
# set basic logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def condition(expr: str) -> dict:
    """
    Webhook condition builder from `str` expression.

    <style>td,th{border:none!important;text-align:left;}</style>
    webhook                   | expr
    ------------------------- | ------------
    `lt` / `lte`              | `<` / `<=`
    `gt` / `gte`              | `>` / `>=`
    `eq` / `ne`               | `==` / `!=`
    `truthy` / `falsy`        | `?` / `!?`
    `REGEXP` / `contains`     | `\\` / `$`
    `between` / `not-between` | `<>` / `!<>`

    ```python
    >>> from mainsail import webhook
    >>> webhook.condition("vendorField\\^.*payroll.*$")
    {'value': '^.*payroll.*$', 'key': 'vendorField', 'condition': 'regexp'}
    >>> webhook.condition("amount<>2000000000000:4000000000000")
    {'value': {'min': '2000000000000', 'max': '4000000000000'}, 'condition': '\
between', 'key': 'amount'}
    ```

    Args:
        expr (str): human readable expression.

    Returns:
        dict: webhook conditions
    """
    condition = {}
    try:
        key, _operator, value = REGEXP.match(expr).groups()
        operator = OPERATORS[_operator]
    except Exception as error:
        LOGGER.info("%r", error)
    else:
        if "between" in operator:
            _min, _max = value.split(":")
            condition["value"] = {"min": _min, "max": _max}
        elif value != "":
            condition["value"] = value
        condition["key"] = key
        condition["condition"] = operator
    return condition


def dump(token: str) -> str:
    # "0c8e74e1cbfe36404386d33a5bbd8b66fe944e318edb02b979d6bf0c87978b64"
    authorization = token[:32]  # "0c8e74e1cbfe36404386d33a5bbd8b66"
    verification = token[32:]   # "fe944e318edb02b979d6bf0c87978b64"
    filename = os.path.join(
        DATA, hashlib.md5(authorization.encode("utf-8")).hexdigest()
    )
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with io.open(filename, "wb") as out:
        pickle.dump(
            {
                "verification": verification,
                "hash": hashlib.sha256(token.encode("utf-8")).hexdigest()
            },
            out
        )
    return filename


def subscribe(peer: dict, event: str, target: str, *conditions) -> None:
    conditions = [
        (
            condition(cond) if isinstance(cond, str) else
            cond if isinstance(cond, dict) else
            {}
        )
        for cond in conditions
    ]
    data = rest.WHKP.api.webhooks(
        peer=peer, event=event, target=target,
        conditions=[cond for cond in conditions if cond],
    ).get("data", {})
    if "token" in data:
        # build the security hash and keep only second token part and
        # save the used peer to be able to delete it later
        data["nethash"] = getattr(rest.config, "nethash")
        data["dump"] = dump(data.pop("token"))
        data["peer"] = peer
        dumpJson(data, os.path.join(DATA, data["id"] + ".json"))
        return data["id"]
    else:
        raise Exception("webhook not created")


def verify(authorization: str) -> bool:
    try:
        filename = os.path.join(
            DATA, hashlib.md5(authorization.encode("utf-8")).hexdigest()
        )
        with io.open(filename, "rb") as in_:
            data = pickle.load(in_)
    except Exception:
        return False
    else:
        token = authorization + data["verification"]
        return \
            hashlib.sha256(token.encode("utf-8")).hexdigest() == data["hash"]


def list() -> list:
    return [
        name.split(".")[0] for name in next(os.walk(DATA))[-1]
        if name.endswith(".json")
    ]


def open(whk_id: str) -> dict:
    return loadJson(os.path.join(DATA, whk_id + ".json"))


def unsubscribe(whk_id: str) -> dict:
    whk_path = os.path.join(DATA, whk_id + ".json")
    if os.path.exists(whk_path):
        data = loadJson(whk_path)
        resp = rest.WHKD.api.webhooks(
            "%s" % whk_id, peer=data.get("peer", None)
        )
        if resp.status_code == 204:
            try:
                os.remove(data["dump"])
            except Exception:
                pass
            os.remove(whk_path)
        return resp
    else:
        raise Exception("cannot find webhook data")


# TODO: implement
def change(self, event=None, target=None, *conditions):
    pass
