#!/bin/bash

# specific versions to lock at 
# note that nodejs comes with npm
YARN_VERSION="1.22.5-1"
NODEJS_VERSION="12.18.4-1nodesource1"

apt -y install curl dirmngr apt-transport-https lsb-release ca-certificates gnupg
curl -sL https://deb.nodesource.com/setup_12.x | bash -
apt-get update

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt-get update

rm build.sh
rm runDocker.sh

mkdir TESTING_REPOS

apt-get -y install nodejs=$NODEJS_VERSION yarn=$YARN_VERSION