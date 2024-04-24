# python-mainsail

This package aims to provide a simple implementation to bake offline `Ark`
transaction and interact with the blockchain API.

```python
>>> from mainsail.tx.v1 import Transfer
>>> from mainsail import rest
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
>>> t = Transfer(1, 'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv', 'message \U0001f919')
>>> t.sign()
Type or paste your passphrase >
>>> t.send()
{'data': {'accept': [0], 'broadcast': [0], 'excess': [], 'invalid': []}}
```

## Validator pool managment tool

Install and deploy server:

```bash
~$ wget https://raw.githubusercontent.com/Moustikitos/python-mainsail/master/mnsl-pool.sh
~$ bash mnsl-pool.sh
~$ mnsl_pool_deploy
```

Add delegate:

```bash
~$ add_validator 02968e862011738ac185e87f47dec61b32c842fd8e24fab625c02a15ad7e2d0f65
Type or paste your passphrase>
enter pin code to secure secret>
provide a valid network peer> http://127.0.0.1:4003
provide a valid webhook peer> http://127.0.0.1:4004
provide a valid target endpoint> http://127.0.0.1:5000/block/forged
```

Check the logs:

```bash
~$ log_mnsl_pool
~$ log_mnsl_bg
```

## [RIPEMD160 issue with OpenSSL v>=3](https://github.com/openssl/openssl/issues/16994) on ubuntu

Get the installation folder:

```bash
openssl version -d
```

Make sure that the openssl config file contains following lines:

```conf
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1
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

## Features

* [x] pool server with remote managment tool
* [x] secured private keys storage
* [x] secured webhook subscriptions storage
* [x] offline network configuration available

## Support this project

<!-- [![Liberapay receiving](https://img.shields.io/liberapay/goal/Toons?logo=liberapay)](https://liberapay.com/Toons/donate) -->
[![Paypal me](https://img.shields.io/badge/PayPal-toons-00457C?logo=paypal&logoColor=white)](https://paypal.me/toons)
[![Bitcoin](https://img.shields.io/badge/Donate-bc1q6aqr0hfq6shwlaux8a7ydvncw53lk2zynp277x-ff9900?logo=bitcoin)](https://github.com/Moustikitos/python-mainsail/blob/master/docs/img/bc1q6aqr0hfq6shwlaux8a7ydvncw53lk2zynp277x.png)
