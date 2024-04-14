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
echo "done"
