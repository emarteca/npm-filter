#!/bin/bash

# specific versions to lock at 
YARN_VERSION="1.22.5-1"
NODEJS_VERSION="12.18.4-1nodesource1"
NPM_VERSION="3.5.2-0ubuntu4"

apt -y install curl dirmngr apt-transport-https lsb-release ca-certificates
curl -sL https://deb.nodesource.com/setup_12.x | bash -

DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends nodejs=$NODEJS_VERSION npm=$NPM_VERSION curl gnupg

alias python=python3
export python

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt update
apt install --no-install-recommends yarn=$YARN_VERSION

rm build.sh
rm runDocker.sh