<a id="pool"></a>

# Module pool

This package provides managment tools to run a pool on arkEcosystem mainsail
framework. It computes a true block weight (TBW) distribution of block reward
according to instant participant vote weight.

## Install on Ubuntu

```bash
wget https://bit.ly/3U6BI8v
bash mnsl-pool.sh
```

Setup script creates 7 commands into `~/.bash_aliases` file:

* [x] `mnsl_pool_deploy` takes broadcast ip address and port to create
  services managed by `systemd`.
* [x] `add_validator` takes a validator public key to configure listening
  subscription on blockchain.
* [x] `mnsl_venv_activate` activates the virtual environment used to run
  mainsail pool.
* [x] `restart_mnsl_pool` restarts the server.
* [x] `restart_mnsl_bg` restarts background tasks.
* [x] `log_mnsl_pool` shows server logs.
* [x] `log_mnsl_bg` shows background tasks logs.

