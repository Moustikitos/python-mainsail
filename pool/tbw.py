# -*- coding: utf-8 -*-
import os
import math
import time
import logging
import datetime

from mainsail import rest, identity, loadJson, dumpJson, XTOSHI
from mainsail.tx import Transfer, MultiPayment

# Set basic logging.
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
DATA = os.path.join(os.getenv("HOME"), ".mainsail", ".pools")


def update_forgery(block: dict) -> bool:
    # 1. GET GENERATOR PUBLIC KEY PARAMETERS
    publicKey = block["generatorPublicKey"]
    info = loadJson(os.path.join(DATA, f"{publicKey}.json"))
    excludes = info.get("excludes", [])
    # Minimum vote and maximum vote have to be converted to Xtoshi.
    min_vote = info.get("min_vote", 1) * XTOSHI
    max_vote = info.get("max_vote", int(1e6)) * XTOSHI
    share = info.get("share", 1.0)
    # Load network.
    rest.load_network(info["nethash"])
    address = identity.get_wallet(publicKey)

    # 2. GET FEES AND REWARDS SINCE LAST FORGED BLOCK
    reward = fees = blocks = 0
    last_block = loadJson(os.path.join(DATA, publicKey, "last.block"))
    # If no block found save the first one and exit.
    if last_block == {}:
        dumpJson(block, os.path.join(DATA, publicKey, "last.block"))
        return False
    i = 1
    while i > 0:
        # Go through all blocks forged by generator public key from the last
        # one the previous ones. This is done when for some reasons the worker
        # didn't parse block sent through node subscription.
        for nexious_block in getattr(
            rest.GET.api.wallets, address
        ).blocks(orderBy="height:desc", page=i).get("data", []):
            if nexious_block["height"] == block["height"] or \
               nexious_block["height"] > last_block["height"]:
                r = int(nexious_block["reward"])
                f = int(nexious_block["fees"])
                LOGGER.info(
                    f"Getting reward<{r / XTOSHI:.8f}> and "
                    f"fee<{f / XTOSHI:.8f}> "
                    f"from block {block['id']}"
                )
                reward += r
                fees += f
                blocks += 1
            # Exit if the highest block in blockchain is below the one sent by
            # webhook or if all unparsed blocks have be parsed.
            else:
                i = 0  # -> exit infinite loop
            i += 1  # - go to next API page
    # Apply the share and dump the block sent by webhook as the last one.
    shared_reward = int(math.floor(reward * share))
    generator_reward = reward - shared_reward
    dumpJson(block, os.path.join(DATA, publicKey, "last.block"))

    # 3. GET VOTER WEIGHTS
    voters = {}
    i = 1
    while i > 0:
        resp = getattr(rest.GET.api.wallets, address).voters(page=i)
        voters.update(
            (v["address"], int(v["balance"])) for v in resp.get("data", [])
            if v["address"] not in excludes
        )
        if resp.get("meta", {}).get("next", None) is None:
            i = 0  # -> exit infinite loop
        i += 1  # - go to next API page
    # filter all voters using minimum and maximum votes
    voters = dict(
        [a, b] for a, b in voters.items() if b >= min_vote and b <= max_vote
    )
    # compute vote weight amongs fltered voters
    vote_weight = float(sum(voters.values()))
    voters_weight = dict([a, b / vote_weight] for a, b in voters.items())

    # 4. UPDATE FORGERY ACCORDING TO REWARDS AND VOTER WEIGHT
    forgery = loadJson(os.path.join(DATA, publicKey, "forgery.json"))
    contributions = forgery.get("contributions", {})
    new_contributions = dict([
        address, int(
            math.floor(
                contributions[address] +
                shared_reward * voters_weight[address]
            )
        )
    ] for address in voters_weight)
    forgery["reward"] = forgery.get("reward", 0) + generator_reward
    forgery["blocks"] = forgery.get("blocks", 0) + blocks
    forgery["fees"] = forgery.get("fees", 0) + fees
    forgery["contributions"] = new_contributions
    dumpJson(forgery, os.path.join(DATA, publicKey, "forgery.json"))

    # 5. PRINT VOTE CHANGES
    for downvoter in list(set(contributions.keys()) - set(voters.keys())):
        LOGGER.info(
            f"{downvoter} downvoted {publicKey} : "
            f"{contributions[downvoter] / XTOSHI:.8f} token leaved"
        )
    for upvoters in list(set(voters.keys()) - set(contributions.keys())):
        LOGGER.info(
            f"{upvoters} upvoted validator - "
            f"{voters[upvoters] / XTOSHI:.8f} vote weight added"
        )

    # Exit with True means 5 steps gone straight.
    return True


def freeze_forgery(puk: str, **options) -> None:
    min_share = options.get("min_share", 1) * XTOSHI
    forgery = loadJson(os.path.join(DATA, puk, "forgery.json"))
    tbw = {
        "timestamp": f"{datetime.datetime.now()}",
        "validator-share": forgery.get("reward", 0) + forgery.get("fees", 0),
        "voter-shares": dict(
            [voter, amount]
            for voter, amount in forgery.get("contributions", {}).items()
            if amount >= min_share
        )
    }
    dumpJson(
        tbw, os.path.join(DATA, puk, f"{time.strftime('%Y%m%d-%H%M')}.forgery")
    )

    forgery.pop("blocks", 0)
    forgery.pop("reward", 0)
    forgery.pop("fees", 0)
    forgery["contributions"] = dict(
        [voter, 0 if voter in tbw["voter-shares"] else amount]
        for voter, amount in forgery.get("contributions", {}).items()
    )
    dumpJson(forgery, os.path.join(DATA, puk, "forgery.json"))


def bake_registry(puk: str) -> None:
    info = loadJson(os.path.join(DATA, f"{puk}.json"))
    names = [
        name.split(".")[0] for name in os.listdir(os.path.join(DATA, puk))
        if name.endswith(".forgery")
    ]
    if len(names):
        prk = identity.KeyRing.load(info.get("prk", None))
        rest.load_network(info["nethash"])
        wallet = rest.GET.api.wallets(puk)
        nonce = int(wallet.get("nonce", 0)) + 1
        for name in names:
            registry = []
            tbw = loadJson(os.path.join(DATA, puk, f"{name}.forgery"))
            share = Transfer(
                tbw["validator-share"] / XTOSHI, wallet["address"],
                f"{puk} reward"
            )
            share.sign(prk, nonce=nonce)
            registry.append(share.serialize())

            message = info.get("message", "Voter share")
            voter_shares = tbw.get("voter-shares", {})
            if len(voter_shares) <= 2:
                for address, amount in voter_shares.items():
                    nonce += 1
                    transfer = Transfer(amount / XTOSHI, address, message)
                    transfer.sign(prk, nonce=nonce)
                    registry.append(transfer.serialize())
            else:
                chunck_size = info.get("chunck_size", 50)
                items = list(voter_shares.items())
                for i in list(range(len(items)))[::chunck_size]:
                    nonce += 1
                    multipayment = MultiPayment(vendorField=message)
                    multipayment.asset["payments"].extend([
                        {"recipientId": address, "amount": amount}
                        for address, amount in items[i:i + chunck_size]
                    ])
                    multipayment.sign(prk, nonce=nonce)
                    registry.append(multipayment.serialize())
            dumpJson(registry, os.path.join(DATA, puk, f"{name}.registry"))
            try:
                dumpJson(
                    tbw, os.path.join(DATA, puk, "forgery", f"{name}.forgery")
                )
            except Exception:
                pass
            else:
                os.remove(os.path.join(DATA, puk, f"{name}.forgery"))


def broadcast_registry() -> None:
    pass
