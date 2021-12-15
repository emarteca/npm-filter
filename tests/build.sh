#!/bin/bash

# specific versions to lock at 
# note that nodejs comes with npm
YARN_VERSION="1.22.17"
NODEJS_VERSION="16.10.0"

apt -y install curl dirmngr apt-transport-https lsb-release ca-certificates gnupg build-essential
curl -sL https://deb.nodesource.com/setup_12.x | bash -
apt-get update

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt-get update

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env

pip3 install --upgrade setuptools setuptools_rust wheel
pip3 install scrapy bs4

rm build.sh
rm runDocker.sh

mkdir TESTING_REPOS

# install specific version of node
# https://askubuntu.com/questions/957439/how-to-install-a-specific-version-of-node-on-ubuntu-server
wget https://nodejs.org/dist/v${NODEJS_VERSION}/node-v${NODEJS_VERSION}-linux-x64.tar.gz
mkdir -p /opt/nodejs
tar -xvzf node-v${NODEJS_VERSION}-linux-x64.tar.gz -C /opt/nodejs
cd /opt/nodejs
mv node-v${NODEJS_VERSION}-linux-x64 ${NODEJS_VERSION}
ln -s ${NODEJS_VERSION} current
ln -s /opt/nodejs/current/bin/node /usr/bin/node

# link npm and use it to install yarn and common testing packages
ln -s /opt/nodejs/current/bin/npm /usr/bin/npm

npm install -g yarn@${YARN_VERSION}
npm install -g jest mocha tap ava nyc 

echo PATH=/opt/nodejs/current/bin/:$PATH >> /root/.bashrc