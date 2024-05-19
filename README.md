# python-mainsail

This package provides a simple implementation to interact with `Ark` blockchain
API and managment tools for validators aiming to [run a pool](https://moustikitos.github.io/python-mainsail/pool).

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
>>> custom_peer = rest.Peer("http://49.13.30.19:4006", port_name="api-development")
>>> custom_peer
{'ip': '49.13.30.19', 'ports': {'api-development': 4006}}
>>> # http://49.13.30.19:4003/api/transactions?type=4
>>> [t["blockId"] for t in rest.GET.api.transactions(type=4, peer=custom_peer)["data"]]
['41afebd995473aab76e8dd7415ab742a6882a08f4c0e0a7305d1a48c551c955c', 'aff37ad0288fadc9d5fdec584d1affab2df0021e86cde3ecb2ba263d6deba3cc']
>>> t = Transfer(1, 'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv', 'message \U0001f919')
>>> t.sign()
Type or paste your passphrase >
>>> t.send()
{'data': {'accept': [0], 'broadcast': [0], 'excess': [], 'invalid': []}}
```

## Linux distributions

Due to [RIPEMD160 issue with OpenSSL v>=3](https://github.com/openssl/openssl/issues/16994),
`hashlib.ripemd160` is disabled within `python3`. To enable it back, get the
installation folder...

```bash
openssl version -d
```

... and make sure that the openssl config file contains following lines:

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

- [x] Transfer
- [x] ValidatorRegistration
- [x] Vote
- [x] MultiSignature
- [x] MultiPayment
- [x] ValidatorResignation
- [x] UsernameRegistration
- [x] UsernameResignation

## Features

- [x] secured private keys storage
- [x] secured webhook subscriptions storage
- [x] offline network configuration available
- [x] pool server with remote managment tool
- [x] `cmd` command line `set_pool` and `dump_prk` for windows platform
- [x] pool installation and update using pip

## Support this project

<!-- [![Liberapay receiving](https://img.shields.io/liberapay/goal/Toons?logo=liberapay)](https://liberapay.com/Toons/donate) -->
[![Paypal me](https://img.shields.io/badge/PayPal-toons-00457C?logo=paypal&logoColor=white)](https://paypal.me/toons)
[![Bitcoin](https://img.shields.io/badge/Donate-bc1q6aqr0hfq6shwlaux8a7ydvncw53lk2zynp277x-ff9900?logo=bitcoin)](https://raw.githubusercontent.com/Moustikitos/python-mainsail/master/docs/img/bc1q6aqr0hfq6shwlaux8a7ydvncw53lk2zynp277x.png)
