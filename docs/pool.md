<a id="mnsl_pool"></a>

# mnsl\_pool

This package provides managment tools to run a pool on arkEcosystem mainsail
framework. It computes a true block weight (TBW) distribution of reward
according to instant participant vote weight.

### Ubuntu installation

First read [installation script](https://bit.ly/3U6BI8v), then:

```bash
~$ bash <(wget -qO- https://bit.ly/3U6BI8v)
```

Setup script creates 8 commands into `~/.bash_aliases` file:

- [x] `mnsl_install` install a specific version
- [x] `mnsl_deploy` takes broadcast ip address and port to create
  services managed by `systemd`.
- [x] `add_pool` takes a validator public key to configure listening
  subscription on blockchain.
- [x] `set_pool` modifies validator TBW pool service parameters.
- [x] `mnsl_venv` activates the virtual environment used to run
  mainsail pool.
- [x] `mnsl_restart` restarts pool tasks.
- [x] `log_mnsl_pool` shows server logs.
- [x] `log_mnsl_bg` shows background tasks logs.

<a id="mnsl_pool.biom"></a>

# biom

<a id="mnsl_pool.biom.deploy"></a>

## deploy

```python
def deploy(host: str = "127.0.0.1", port: int = 5000)
```

**Deploy pool server**

```python
>>> from mnsl_pool import biom
>>> biom.deploy()
```

```bash
~$ mnsl_deploy # use ip address 0.0.0.0 with port `5000`
```

If you plan to deploy pool server behind a proxy, it is possible to
customize `ip` and `port`:

```bash
~$ mnsl_deploy host=127.0.0.1 port=7542 # use localhost address with port `7542`
```

<a id="mnsl_pool.biom.add_pool"></a>

## add\_pool

```python
def add_pool(**kwargs) -> None
```

**Initialize a pool**

```python
>>> from mnsl_pool import biom
>>> biom.add_pool(puk="033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504db")
```

```bash
~$ add_pool puk=033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504dbba5477ba
```

```
INFO:mnsl_pool.biom:grabed options: {'puk': '033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504dbba5477ba'}
Type or paste your passphrase >
enter pin code to secure secret (only figures)>
provide a network peer API [default=localhost:4003]>
provide your webhook peer [default=localhost:4004]>
provide your target server [default=localhost:5000]>
INFO:mnsl_pool.biom:grabed options: {'prk': [0, 0, 0, 0], 'nethash': '7b9a7c6a14d3f8fb3f47c434b8c6ef0843d5622f6c209ffeec5411aabbf4bf1c', 'webhook': '47f4ede0-1dcb-4653-b9a2-20e766fc31d5', 'puk': '033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504dbba5477ba'}
INFO:mnsl_pool.biom:delegate 033f786d4875bcae61eb934e6af74090f254d7a0c955263d1ec9c504dbba5477ba set
```

Check your pool using two endpoits:

```bash
http://{ip}:{port}/{puk or username}
http://{ip}:{port}/{puk or username}/forgery
```

Pool data are stored in `~/.mainsail` folder.

<a id="mnsl_pool.biom.set_pool"></a>

## set\_pool

```python
def set_pool(**kwargs) -> requests.Response
```

**Configure a pool**

```python
>>> from mnsl_pool import biom
>>> addresses = [
... "D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv",
... "DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU"
... ]
>>> biom.set_pool(share=0.7, min_vote=10.0, exlusives=addresses)
```

```bash
$ set_pool --share=0.7 --min-vote=10.0 --exclusives=D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv,DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU
```

```
INFO:pool.biom:grabed options: {'share': 0.7, 'min_vote': 10.0, 'exclusives': 'D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv,DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU'}
enter validator security pincode>
{'status': 204, 'updated': {'exclusives': ['D5Ha4o3UTuTd59vjDw1F26mYhaRdXh7YPv', 'DTGgFwrVGf5JpvkMSp8QR5seEJ6tCAWFyU'], 'min_vote': 10.0, 'share': 0.7}}
```

available parameters:

- [x] `share` - share rate in float number (0. <= share = 1.0).
- [x] `min_vote` - minimum vote to be considered by the pool.
- [x] `max_vote` - maximum vote weight caped in the pool.
- [x] `min_share` - minimum reward to reach for a vote wallet to be
      included in payroll.
- [x] `excludes` - comma-separated list of wallet to exclude.
- [x] `exclusives` - comma-separated list of private pool wallets.
- [x] `block_delay` - number of forged block between two payrolls.
- [x] `message` - vendorFied message to be set on each payroll transacion.
- [x] `chunck_size` - maximum number of recipient for a multipayment.
- [x] `wallet` - custom wallet to receive validator share.

**`excludes` & `exclusives`**

Those parameter accept a custom action to add or remove item from list.

```bash
(excludes|exclusives):[add|pop]=coma,separated,list,of,valid,addresses
```

