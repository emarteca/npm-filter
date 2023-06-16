#!/bin/bash

# can be building for one specific repo, at a specific commit 
# (if theyre not specified theyre just empty string, that's fine)
repo_link=$1
repo_commit=$2

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

# cd /home/codeql_home
# curl -L -o codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/download/v2.3.4/codeql-linux64.zip
# unzip codeql-linux64.zip 
# # clone stable version
# git clone https://github.com/github/codeql.git --branch v1.26.0 codeql-repo

apt -y install curl dirmngr apt-transport-https lsb-release ca-certificates gnupg build-essential
apt-get update

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
apt-get update

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env

pip3 install --upgrade setuptools setuptools_rust wheel

echo "alias python=python3" >> /root/.bashrc
echo "alias ipython=ipython3" >> /root/.bashrc
echo "alias vi=vim" >> /root/.bashrc

cd /home/npm-filter

if [ -d TESTING_REPOS ]; then
	rm -rf TESTING_REPOS
fi 
mkdir TESTING_REPOS

node_version='v18.16.0' # default to just the latest LTS version
npm_version='*'
# if there's a repo_link specified
if [ ! -z "$repo_link" ]; then
	cd TESTING_REPOS
	git clone $repo_link
	# repo dir will be the only thing in TESTING_REPOS
	repo_dir_name=`ls`
	if [ ! -z "$repo_commit" ]; then
		cd $repo_dir_name
		git checkout $repo_commit
	fi
	cd /home/npm-filter

	# this will make the node_version and npm_version variables
	# it's ok to use the generic version here -- just using it for the vars
	# need these dependencies for my get_rel_project_reqs.js script
	nvm install $node_version
	nvm use $node_version
	nvm install-latest-npm

	npm install semver node-fetch

	# script to set the env variables for node_version etc
	echo "#!/bin/bash" > req_vars.sh
	node get_rel_project_reqs.js TESTING_REPOS/${repo_dir_name} >> req_vars.sh
	chmod 700 req_vars.sh
	# source in current shell: so we set the variables in the current shell
	. req_vars.sh
	rm req_vars.sh

	echo $node_version
	`$set_req_vars`
	rm -r node_modules

	if [[ $node_version == "*" ]]; then
		node_version=node
	fi
fi

# set up node and npm, and also add this node/npm config to the bashrc 
# so that it runs on docker startup too 

nvm install $node_version
nvm use $node_version

if [[ $npm_version == "*" ]]; then
	nvm install-latest-npm
else
	npm install -g npm@${npm_version}
fi

NVM_DIR=/root/.nvm
NODE_VERSION=`node --version`

echo "export NODE_VERSION=\"$NODE_VERSION\"" >> /envfile
echo "export NVM_DIR=$NVM_DIR" >> /envfile
echo "export NODE_PATH=$NVM_DIR/$NODE_VERSION/lib/node_modules" >> /envfile
echo "export PATH=$NVM_DIR/$NODE_VERSION/bin:/home/codeql_home/codeql:$PATH" >> /envfile

cat /envfile >> /root/.bashrc

# permissive
npm config set strict-ssl false

# install the dependencies: but use the current version of npm
npm install -g jest mocha tap ava nyc yarn next

config_file=configs/build_only_config.json
if [ -f "/home/npm-filter/configs/custom_install_script" ]; then
	chmod +x /home/npm-filter/configs/custom_install_script
	config_file=configs/custom_install_only.json
fi

if [ ! -z "$repo_link" ]; then 
	cd /home/npm-filter
	# do the install and build only (build_only_config.json config file)
	if [ ! -z "$repo_commit" ]; then
        python3 src/diagnose_github_repo.py --repo_link_and_SHA $repo_link $repo_commit --config $config_file --output_dir results
    else 
        python3 src/diagnose_github_repo.py --repo_link $repo_link --config $config_file --output_dir results
    fi
fi

