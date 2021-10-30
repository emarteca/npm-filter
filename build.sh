#!/bin/bash

rm build.sh
rm Dockerfile
rm runDocker.sh
rm -r local_mount

mkdir -p /home/codeql_home

cd /home/codeql_home
curl -L -o codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/download/v2.3.4/codeql-linux64.zip
unzip codeql-linux64.zip 
# clone stable version
git clone https://github.com/github/codeql.git --branch v1.26.0 codeql-repo

echo "export PATH=/home/codeql_home/codeql:$PATH" >> /root/.bashrc
echo "alias python=python3" >> /root/.bashrc
echo "alias ipython=ipython3" >> /root/.bashrc
echo "alias vi=vim" >> /root/.bashrc

cd /home/npm-filter