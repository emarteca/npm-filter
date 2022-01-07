#!/bin/bash

rm build.sh
rm Dockerfile
rm runDocker.sh
if [ -d local_mount ]; then
	rm -r local_mount
fi

mkdir -p /home/codeql_home

cd /home/codeql_home
curl -L -o codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/download/v2.3.4/codeql-linux64.zip
unzip codeql-linux64.zip 
# clone stable version
git clone https://github.com/github/codeql.git --branch v1.26.0 codeql-repo

apt -y install curl dirmngr apt-transport-https lsb-release ca-certificates gnupg build-essential
curl -sL https://deb.nodesource.com/setup_12.x | bash -
apt-get update

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt-get update

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env

pip3 install --upgrade setuptools setuptools_rust wheel

npm install -g jest mocha tap ava nyc yarn

echo "export PATH=/home/codeql_home/codeql:$PATH" >> /root/.bashrc
echo "alias python=python3" >> /root/.bashrc
echo "alias ipython=ipython3" >> /root/.bashrc
echo "alias vi=vim" >> /root/.bashrc

cd /home/npm-filter
