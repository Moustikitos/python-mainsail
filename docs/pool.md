<a id="mnsl_pool"></a>

# mnsl\_pool

This package provides managment tools to run a pool on arkEcosystem mainsail
framework. It computes a true block weight (TBW) distribution of block reward
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

### Deploy pool server

```bash
~$ mnsl_deploy # use ip address 0.0.0.0 with port `5000`
```

If you plan to deploy pool server behind a proxy, it is possible to customize
`ip` and `port`:

```bash
~$ mnsl_deploy host=127.0.0.1 port=7542 # use localhost address with port `7542`
```

### Check your pool

A simple JSON server provides two endpoits:

```bash
http://{ip}:{port}/{puk}
http://{ip}:{port}/{puk}/forgery
```

Pool data are stored in `~/.mainsail` folder.

<a id="mnsl_pool.pool_configure"></a>

## pool\_configure

```python
@app.route("/pool/configure", methods=["POST"])
def pool_configure() -> flask.Response
```

Flask endpoint to configure validator pool parameters. Requests are secured
using validator signature on UTC-time-based nonce. Available parameters are
set in `pool.biom:POOL_PARAMETERS` dict.

This endpoint is used by `set_pool` command.

<a id="mnsl_pool.biom"></a>

# mnsl\_pool.biom

<a id="mnsl_pool.biom.set_pool"></a>

## set\_pool

```python
def set_pool(**kwargs) -> requests.Response
```

```python
>>> from mnsl_pool import biom
>>> biom.set_pool(share=0.7, min_vote=10.0)
```

```bash
$ set_pool ?key=value?
```

**Pool parameters:**

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

