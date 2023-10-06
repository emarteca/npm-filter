#!/bin/bash

npm_filter_command=$@

if [ ! -d local_mount ]; then
	mkdir local_mount
fi

# create the dir ourselves so we have write privilege to it
if [ ! -d npm_filter_docker_results ]; then
	mkdir npm_filter_docker_results
fi

if [ -v $DOCKER_IMAGE ]; then
	DOCKER_IMAGE=emarteca/npm-filter:latest
fi

docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount \
		   --volume `pwd`/npm_filter_docker_results:/home/npm-filter/results \
		   --volume `pwd`/docker_configs:/home/npm-filter/docker_configs\
		   -w /home/npm-filter \
		   $DOCKER_IMAGE \
		   bash -c "source /envfile; PATH=/home/codeql_home/codeql:\$PATH; $npm_filter_command --output_dir results"
rm -r local_mount