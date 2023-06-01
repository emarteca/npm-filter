#!/bin/bash

# can be building for one specific repo
repo_link=$1

# install nvm, so we can then use specific versions of node and npm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | /usr/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # this loads nvm


rm build.sh
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
apt-get update

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt-get update

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env

pip3 install --upgrade setuptools setuptools_rust wheel

echo "export PATH=/home/codeql_home/codeql:$PATH" >> /root/.bashrc
echo "alias python=python3" >> /root/.bashrc
echo "alias ipython=ipython3" >> /root/.bashrc
echo "alias vi=vim" >> /root/.bashrc

cd /home/npm-filter

repo_dir_name=SPEC_REPO_DIR
node_version='node' # default to just the latest version
npm_version='*'
# if there's a repo_link specified
if [ -n $repo_link ]; then
	git clone $repo_link $repo_dir_name
	# this will make the node_version and npm_version variables
	set_req_vars=`node get_rel_project_reqs.js $repo_dir_name 2>/dev/null`
	`$set_req_vars`

	if [[ $node_version == "*" ]]; then
		node_version=node
	fi
fi

# set up node and npm, and also add this node/npm config to the bashrc 
# so that it runs on docker startup too 

nvm install $node_version
nvm use $node_version
echo "nvm use $node_version" >> /root/.bashrc

if [[ $npm_version == "*" ]]; then
	nvm install-latest-npm
	echo "nvm install-latest-npm" >> /root/.bashrc
else
	npm install -g npm@${npm_version}
	echo "npm install -g npm@${npm_version}" >> /root/.bashrc
fi


# permissive
npm config set strict-ssl false

# install the dependencies: but use the current version of npm
npm install -g jest mocha tap ava nyc yarn next semver

if [ -n $repo_link ]; then 
	cd $repo_dir_name
	# setup the project
	if [ -f "yarn.lock" ]; then
		yarn > /dev/null 
	else 
		npm install > /dev/null
	fi
	cd ..
fi

