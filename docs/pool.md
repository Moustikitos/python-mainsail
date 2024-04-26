<a id="pool"></a>

# pool

This package provides managment tools to run a pool on arkEcosystem mainsail
framework. It computes a true block weight (TBW) distribution of block reward
according to instant participant vote weight.

## Install on Ubuntu

```bash
wget https://bit.ly/3U6BI8v
bash mnsl-pool.sh
```

Setup script creates 7 commands into `~/.bash_aliases` file:

* [x] `mnsl_deploy` takes broadcast ip address and port to create
  services managed by `systemd`.
* [x] `add_pool` takes a validator public key to configure listening
  subscription on blockchain.
* [x] `set_pool` modifies validator TBW pool service parameters.
* [x] `mnsl_venv` activates the virtual environment used to run
  mainsail pool.
* [x] `mnsl_restart` restarts pool tasks.
* [x] `log_mnsl_pool` shows server logs.
* [x] `log_mnsl_bg` shows background tasks logs.

<a id="pool.pool_configure"></a>

## pool\_configure

```python
@app.route("/pool/configure", methods=["POST"])
def pool_configure() -> flask.Response
```

Flask endpoint to configure validator pool parameters. Requests are secured
using validator signature on UTC-time-based nonce. Available parameters are
set in `pool.biom:DELEGATE_PARAMETERS` dict.

This end point is used by `set_pool` command:

```bash
$ set_pool ?key=value?
```

Available keys:

* [x] `share` - share rate in float number (0. <= share = 1.0).
* [x] `min_vote` - minimum vote to be considered by the pool.
* [x] `max_vote` - maximum vote weight caped in the pool.
* [x] `min_share` - minimum reward to reach for a vote wallet to receive
      token.
* [x] `excludes` - comma-separated list of wallet to exclude.
* [x] `block_delay` - number of forged block between two payrolls
* [x] `message` - vendorFied message to be set on each payroll transacion
* [x] `chunck_size` - maximum number of recipient for a multipayment
* [x] `wallet` - custom wallet to receive validator share

<a id="pool.main"></a>

## main

```python
def main()
```

Server main loop ran as a `threading.Thread` target. It gets block
passed by `block_forged` (`/block/forged` endpoint) and update forgery
of validator issuing the block.

