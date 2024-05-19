# -*- coding: utf-8 -*-

import os
import time
import queue
import threading

from mainsail import rest
from mnsl_pool import tbw, biom, loadJson, dumpJson, LOGGER

TASK = queue.Queue()
SLEEP = threading.Event()


def payroll():
    while True:
        delay = TASK.get()
        if delay in [False, None]:
            break
        elif isinstance(delay, int):
            if TASK.qsize() == 0:
                TASK.put(delay)
            LOGGER.info(
                f"entering in sleeping time<{delay}s> before forgery check..."
            )
            SLEEP.wait(delay)
            LOGGER.info("sleep time finished, checking forgery...")
            for filename in [
                name for name in os.listdir(tbw.DATA)
                if name.endswith(".json")
            ]:
                puk = filename.split(".")[0]
                info = loadJson(os.path.join(tbw.DATA, filename))
                rest.load_network(info["nethash"])
                forgery = loadJson(os.path.join(tbw.DATA, puk, "forgery.json"))
                blocks = forgery.get("blocks", 0)
                block_delay = info.get("block_delay", 1000)
                LOGGER.info(
                    f"{puk}: "
                    f"block delay<{block_delay}> - forged blocks<{blocks}>"
                )
                if blocks > block_delay:
                    lock = biom.acquireLock()
                    try:
                        if "puk" in info:
                            tbw.freeze_forgery(**info)
                        else:
                            tbw.freeze_forgery(puk, **info)
                    except Exception:
                        LOGGER.exception("---- error occured>")
                    else:
                        LOGGER.info(f"{puk} forgery frozen")
                    finally:
                        biom.releaseLock(lock)
                    tbw.bake_registry(puk)
                    tbw.broadcast_registry(puk)
    LOGGER.info("payroll loop exited")


def accountant():
    while True:
        delay = TASK.get()
        if delay in [False, None]:
            break
        elif isinstance(delay, int):
            if TASK.qsize() == 0:
                TASK.put(delay)
            LOGGER.info(
                f"entering in sleeping time<{delay}s> before registry check..."
            )
            SLEEP.wait(delay)
            LOGGER.info("sleep time finished, checking registries...")
            for filename in [
                name for name in os.listdir(tbw.DATA)
                if name.endswith(".json")
            ]:
                puk = filename.split(".")[0]
                info = loadJson(os.path.join(tbw.DATA, filename))
                rest.load_network(info["nethash"])
                for check in [
                    name for name in os.listdir(os.path.join(tbw.DATA, puk))
                    if name.endswith(".check")
                ]:
                    ids = loadJson(os.path.join(tbw.DATA, puk, check))
                    for tx_id in ids[::]:
                        LOGGER.info(f"transaction {tx_id} applied")
                        if rest.GET.api.transactions(
                            tx_id, peer=tbw.PEER
                        ).get("data", {}).get("confirmations") > 10:
                            ids.pop(ids.index(tx_id))
                    if len(ids) > 0:
                        dumpJson(ids, os.path.join(tbw.DATA, puk, check))
                    else:
                        registry = check.replace(".check", "")
                        dumpJson(
                            loadJson(os.path.join(tbw.DATA, puk, registry)),
                            os.path.join(tbw.DATA, puk, "registry", registry)
                        )
                        os.remove(os.path.join(tbw.DATA, puk, registry))
                        os.remove(os.path.join(tbw.DATA, puk, check))
    LOGGER.info("accountant loop exited")


def stop():
    LOGGER.info("---- background tasks stopped")
    TASK.put(False)
    TASK.put(False)
    TASK.get()
    SLEEP.set()


conf = loadJson(os.path.join(tbw.DATA, ".conf"))
TASK.put(conf.get("sleep_time", 5*60))

payroll_task = threading.Thread(target=payroll)
accountant_task = threading.Thread(target=accountant)

payroll_task.daemon = True
accountant_task.daemon = True

LOGGER.info("---- background tasks started")
payroll_task.start()
accountant_task.start()

while not SLEEP.is_set():
    try:
        time.sleep(1)
        if not (payroll_task.is_alive() and accountant_task.is_alive()):
            stop()
    except KeyboardInterrupt:
        stop()
