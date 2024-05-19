# -*- coding: utf-8 -*-
import os
import math
import time
import random
import logging
import datetime
import binascii

from mainsail import rest, identity, loadJson, dumpJson, XTOSHI
from mainsail.tx import Transfer, MultiPayment

# Set basic logging.
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
DATA = os.path.join(os.getenv("HOME"), ".mainsail", ".pools")
PEER = rest.Peer("http://127.0.0.1:4003")  # {"ip": "127.0.0.1", "ports": {"api-http": 4003}}

os.makedirs(DATA, exist_ok=True)


class UnknownValidator(Exception):
    pass


def update_forgery(block: dict) -> bool:
    # 1. GET GENERATOR PUBLIC KEY PARAMETERS
    publicKey = block["generatorPublicKey"]
    info = loadJson(os.path.join(DATA, f"{publicKey}.json"))
    if info == {}:
        raise UnknownValidator(f"{publicKey} has no subcription here")
    excludes = info.get("excludes", [])  # public pool
    exclusives = info.get("exclusives", [])  # private pool
    filter_addr = \
        (lambda addr: addr in exclusives) if exclusives else \
        (lambda addr: addr not in excludes)
    # Minimum vote and maximum vote have to be converted to Xtoshi.
    min_vote = info.get("min_vote", 1) * XTOSHI
    max_vote = info.get("max_vote", int(1e6)) * XTOSHI
    share = info.get("share", 1.0)
    peer = info.get("api_peer", PEER)

    # 2. GET FEES AND REWARDS SINCE LAST FORGED BLOCK
    last_block = loadJson(os.path.join(DATA, publicKey, "last.block"))
    # If no block found save the first one and exit.
    if last_block == {}:
        dumpJson(block, os.path.join(DATA, publicKey, "last.block"))
        return False
    # Load network.
    rest.load_network(info["nethash"])
    blocks = 1
    reward = int(block["reward"])
    fee = int(block["totalFee"])
    # get all unparsed blocks till the last forged
    unparsed_blocks, page, last_height = [], 1, last_block["height"]
    while page > 0:  # infinite loop
        resp = rest.GET.api.delegates(
            publicKey, "blocks", orderBy="height:desc", page=page, limit=100,
            peer=peer
        )
        filtered_blocks = [
            b for b in resp.get("data", [])
            if b["height"] > last_height and b["height"] < block["height"]
        ]
        unparsed_blocks.extend(filtered_blocks)
        if len(filtered_blocks) < 100:
            break  # -> exit infinite loop
        page += 1  # -> go to next API page
    # extract fees and rewards from unparsed blocks
    LOGGER.debug(f"---- found {len(unparsed_blocks)} unparsed blocks")
    blocks += len(unparsed_blocks)
    for unparsed_block in unparsed_blocks:
        forged = unparsed_block["forged"]
        r = int(forged["reward"])
        f = int(forged["fee"])
        LOGGER.info(
            f"Getting reward<{r / XTOSHI:.8f}> and "
            f"fee<{f / XTOSHI:.8f}> "
            f"from block {unparsed_block['id']}"
        )
        reward += r
        fee += f
    # Apply the share and dump the block sent by webhook as the last one.
    shared_reward = int(math.floor(reward * share))
    generator_reward = reward - shared_reward

    # 3. GET VOTER WEIGHTS
    voters, page = {}, 1
    while page > 0:  # infinite loop
        resp = rest.GET.api.delegates(
            publicKey, "voters", page=page, peer=peer
        )
        voters.update(
            (v["address"], int(v["balance"])) for v in resp.get("data", [])
            if filter_addr(v["address"])  # not in excludes
        )
        if resp.get("meta", {}).get("next", None) is None:
            break  # -> exit infinite loop
        page += 1  # -> go to next API page
    # filter all voters using minimum and maximum votes
    voters = dict(
        [a, min(max_vote, b)] for a, b in voters.items() if b >= min_vote
    )
    LOGGER.debug(f"---- found {len(voters)} valid voters")
    # compute vote weight amongs fltered voters
    vote_weight = float(sum(voters.values()))
    voter_weights = dict([a, b / vote_weight] for a, b in voters.items())
    n_voters = len(voter_weights)

    # 4. UPDATE FORGERY ACCORDING TO REWARDS AND VOTER WEIGHT
    forgery = loadJson(os.path.join(DATA, publicKey, "forgery.json"))
    contributions = forgery.get("contributions", {})
    new_contributions = dict([
        address, int(
            math.floor(
                contributions.get(address, 0) +
                shared_reward * voter_weights[address]
            )
        )
    ] for address in voter_weights)
    forgery["reward"] = forgery.get("reward", 0) + generator_reward
    forgery["blocks"] = forgery.get("blocks", 0) + blocks
    forgery["fee"] = forgery.get("fee", 0) + fee
    # compute checksum to determine lost XTOSHI due to roundings then
    # redistribute XTOSHI if possible
    checksum = (sum(new_contributions.values()) + forgery["reward"])
    checksum -= int(rest.config.constants["reward"]) * forgery["blocks"]
    checksum -= forgery.get("undistributed", 0)
    checksum = abs(checksum)
    if checksum >= n_voters:  # can give n XTOSHI per voter
        xtoshis = int(checksum // n_voters)
        for k in new_contributions:
            new_contributions[k] += xtoshis
        checksum -= n_voters * xtoshis
        LOGGER.info(f"lost XTOSHI redistributed: {n_voters * xtoshis}")
    LOGGER.info(f"lost XTOSHI remaining: {checksum}")
    forgery["contributions"] = new_contributions
    forgery["lost XTOSHI"] = checksum
    # update true block weight state
    dumpJson(block, os.path.join(DATA, publicKey, "last.block"))
    dumpJson(forgery, os.path.join(DATA, publicKey, "forgery.json"))
    LOGGER.info(
        f"{shared_reward / XTOSHI} coin distributed to {len(voters)} voters "
        f"- {generator_reward / XTOSHI} coin plus {fee / XTOSHI} fee added "
        f"to {info.get('wallet', identity.get_wallet(publicKey))} share"
    )

    # 5. PRINT VOTE CHANGES
    for downvoter in list(set(contributions.keys()) - set(voters.keys())):
        LOGGER.info(
            f"{downvoter} downvoted {publicKey} : "
            f"{contributions[downvoter] / XTOSHI:.8f} coin leaved"
        )
    for upvoters in list(set(voters.keys()) - set(contributions.keys())):
        LOGGER.info(
            f"{upvoters} upvoted validator - "
            f"{voters[upvoters] / XTOSHI:.8f} vote weight added"
        )

    # Exit with True means 5 steps gone straight.
    return True


def freeze_forgery(puk: str, **options) -> None:
    min_share = options.get("min_share", 1.0) * XTOSHI
    forgery = loadJson(os.path.join(DATA, puk, "forgery.json"))
    # give lost xtoshi to a random voter
    lost_xtoshi = forgery.pop("lost XTOSHI", 0)
    if lost_xtoshi > 0:
        address = random.choice(list(forgery["contributions"].keys()))
        forgery["contributions"][address] += lost_xtoshi
        LOGGER.info(f"lucky {address} got {lost_xtoshi} XTOSHI")
    tbw = {
        "timestamp": f"{datetime.datetime.now()}",
        "validator-share": forgery.get("reward", 0) + forgery.get("fee", 0),
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
    forgery.pop("fee", 0)
    contributions = dict(
        [voter, 0 if voter in tbw["voter-shares"] else amount]
        for voter, amount in forgery.get("contributions", {}).items()
    )
    forgery["contributions"] = contributions
    forgery["undistributed"] = sum(contributions.values())
    LOGGER.info(
        f"forgery frozen @ {time.strftime('%Y%m%d-%H%M')} - "
        f"{forgery['undistributed']} XTOSHI undistributed"
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
            LOGGER.info(f"baking registry for {name} frozen forgery...")
            registry = []
            tbw = loadJson(os.path.join(DATA, puk, f"{name}.forgery"))
            share = Transfer(
                tbw["validator-share"] / XTOSHI,
                info.get("wallet", wallet["address"]),
                f"\U0001f4b3 {wallet.get('username', puk)} reward"
            )
            share.sign(prk, nonce=nonce)
            registry.append(share.serialize())

            message = info.get(
                "message", f"\U0001f4b3 {wallet.get('username', puk)} share"
            )
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
            LOGGER.info(f"{len(registry)} transactions baked")


def broadcast_registry(puk: str) -> None:
    for registry in [
        reg for reg in os.listdir(os.path.join(DATA, puk))
        if reg.endswith(".registry")
    ]:
        tx = loadJson(os.path.join(DATA, puk, registry))
        LOGGER.info(rest.POST.api("transaction-pool", transactions=tx))
        hash = identity.cSecp256k1.hash_sha256
        dumpJson(
            [hash(binascii.unhexlify(s)).decode("utf-8") for s in tx],
            os.path.join(DATA, puk, f"{registry}.check")
        )
