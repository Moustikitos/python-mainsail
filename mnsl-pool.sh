#!/bin/bash

VENVDIR="$HOME/.local/share/mnsl-pool/venv"
clear
if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "github branch to use : $B"

echo
echo creating commands
echo =================
if [ ! -f ~/.bash_aliases ]; then
    touch ~/.bash_aliases
fi
if [ "$(type -t mnsl_venv)" != 'alias' ]; then
    echo "alias mnsl_venv=\". ~/.local/share/mnsl-pool/venv/bin/activate\"" >> ~/.bash_aliases
fi
if [ "$(type -t mnsl_restart)" != 'alias' ]; then
        echo "alias mnsl_restart=\"sudo systemctl restart mnsl-srv.service ; sudo systemctl restart mnsl-bg.service\"" >> ~/.bash_aliases
fi
if [ "$(type -t log_mnsl_srv)" != 'alias' ]; then
    echo "alias log_mnsl_srv=\"journalctl -u mnsl-srv.service -ef\"" >> ~/.bash_aliases
fi
if [ "$(type -t log_mnsl_bg)" != 'alias' ]; then
    echo "alias log_mnsl_bg=\"journalctl -u mnsl-bg.service -ef\"" >> ~/.bash_aliases
fi
if [ "$(type -t mnsl_deploy)" != 'function' ]; then
    echo "function mnsl_deploy() { mnsl_venv && python -c \"from mnsl_pool import biom;biom.deploy()\" \$@; deactivate ; }" >> ~/.bash_aliases
fi
if [ "$(type -t add_pool)" != 'function' ]; then
    echo "function add_pool() { mnsl_venv && python -c \"from mnsl_pool import biom;biom.add_pool()\" \$@; deactivate ; }" >> ~/.bash_aliases
fi
if [ "$(type -t set_pool)" != 'function' ]; then
    echo "function set_pool() { mnsl_venv && python -c \"from mnsl_pool import biom;print(biom.set_pool())\" \$@ ; deactivate ; }" >> ~/.bash_aliases
fi
echo "done"

echo
echo installing system dependencies
echo ==============================
sudo apt-get update -y
sudo apt-get -q install python3 python3-dev python3-setuptools python3-pip
sudo apt-get -q install libgmp3-dev
sudo apt-get -q install virtualenv
sudo apt-get -q install nginx
echo "done"

echo
echo creating virtual environment
echo ============================
if [ -d $VENVDIR ]; then
    read -p "remove previous virtual environement ? [y/N]> " r
    case $r in
    y) rm -rf $VENVDIR;;
    Y) rm -rf $VENVDIR;;
    *) echo -e "previous virtual environement keeped";;
    esac
fi
if [ ! -d $VENVDIR ]; then
    mkdir $VENVDIR -p
    virtualenv -p "$(which python3)" $VENVDIR
fi
echo "done"

echo
echo installing python dependencies
echo ==============================
. ~/.local/share/mnsl-pool/venv/bin/activate
python -m pip install flask
python -m pip install "git+https://github.com/Moustikitos/python-mainsail.git@$B"
deactivate
echo "done"

. ~/.bashrc
