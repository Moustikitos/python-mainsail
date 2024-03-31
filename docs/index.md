# python-mainsail

This package aims to provide a simple implementation to bake offline `Ark`
transaction and interact with the blockchain API.

## REST API

```python
>>> from mainsail import rest
>>> rest.use_network("http://49.13.30.19:4003")
```

### GET

```python
>>> # http://xxx.xxx.xxx.xxx:4006/api/wallets/toons
>>> wallet = rest.GET.api.wallets.toons()
>>> wallet["address"]
'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv'
>>> rest.GET.api.wallets()["meta"]["totalCount"]
89
>>> # use a custop peer
>>> custom_peer = {"ip": "49.13.30.19", "ports": {"api-development": 4003}}
>>> # http://49.13.30.19:4003/api/transactions?type=4
>>> [t["blockId"] for t in rest.GET.api.transactions(type=4, peer=custom_peer)["data"]]
['41afebd995473aab76e8dd7415ab742a6882a08f4c0e0a7305d1a48c551c955c', 'aff37ad0288fadc9d5fdec584d1affab2df0021e86cde3ecb2ba263d6deba3cc']
```

### POST

```python
>>> from mainsail.tx.v1 import Transfer
>>> t = Transfer(1, 'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv', 'message \U0001f919')
>>> t.sign()
Type or paste your passphrase >
>>> # http://xxx.xxx.xxx.xxx:4007/api/transaction-pool
>>> rest.POST.api("transaction-pool", transactions=[t.serialize()])
{'data': {'accept': [0], 'broadcast': [0], 'excess': [], 'invalid': []}}
```

## Available transactions

* [x] Transfer
* [x] ValidatorRegistration
* [x] Vote
* [x] MultiSignature
* [x] MultiPayment
* [x] ValidatorResignation
* [x] UsernameRegistration
* [x] UsernameResignation
