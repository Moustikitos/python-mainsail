#!/bin/bash

VENVDIR="$HOME/.local/share/mnsl-pool/venv"
GITREPO="https://github.com/Moustikitos/python-mainsail.git"

clear

if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "github branch to use : $B"

echo
echo installing system dependencies
echo ==============================
sudo apt-get update -y
sudo apt-get -qq install python3 python3-dev python3-setuptools python3-pip
sudo apt-get -qq install libgmp3-dev
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx
echo "done"

echo
echo downloading python-mainsail package
echo ===================================

cd ~
if (git clone --branch $B $GITREPO) then
    echo "package cloned !"
else
    echo "package already cloned !"
fi

cd ~/python-mainsail
git reset --hard
git fetch --all
if [ "$B" == "master" ]; then
    git checkout $B -f
else
    git checkout tags/$B -f
fi
git pull

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
    TARGET="$(which python3)"
    mkdir $VENVDIR -p
    virtualenv -p $TARGET $VENVDIR -q
fi

echo "done"

echo
echo installing python dependencies
echo ==============================
. $VENVDIR/bin/activate
export PYTHONPATH=${HOME}/python-mainsail
cd ~/python-mainsail
pip install -r requirements.txt -q
pip install flask -q
deactivate
echo "done"

if [ ! -f ~/.bash_aliases ]; then
    echo
    echo creating commands
    echo =================

    touch ~/.bash_aliases
    echo "function mnsl_pool_deploy() { . ~/.local/share/mnsl-pool/venv/bin/activate && cd ~/python-mainsail && python -c \"from pool import biom;biom.deploy('\${1:-0.0.0.0}', int('\${2:-5000}'))\" ; deactivate ; cd ~ ; }" > ~/.bash_aliases
    echo "function add_validator() { . ~/.local/share/mnsl-pool/venv/bin/activate && cd ~/python-mainsail && python -c \"from pool import biom;biom.add_delegate('\$1')\" ; deactivate ; cd ~ ; }" >> ~/.bash_aliases
    echo "function set_validator() { . ~/.local/share/mnsl-pool/venv/bin/activate && cd ~/python-mainsail && python -c \"from pool import biom;biom.set_delegate()\" \$@ ; deactivate ; cd ~ ; }" >> ~/.bash_aliases
    echo "alias log_mnsl_pool=\"journalctl -u mnsl-pool.service -ef\"" >> ~/.bash_aliases
    echo "alias log_mnsl_bg=\"journalctl -u mnsl-bg.service -ef\"" >> ~/.bash_aliases
    echo "alias restart_mnsl_pool=\"sudo systemctl restart mnsl-pool.service\"" >> ~/.bash_aliases
    echo "alias restart_mnsl_bg=\"sudo systemctl restart mnsl-bg.service\"" >> ~/.bash_aliases
    echo "alias mnsl_venv=\". ~/.local/share/mnsl-pool/venv/bin/activate\"" >> ~/.bash_aliases

    echo "done"
    . ~/.bashrc
fi
