#!/bin/bash

npm_filter_command=$@

mkdir local_mount
docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount \
		   --volume `pwd`/npm_filter_docker_results:/home/npm-filter/results \
		   -w /home/npm-filter \
		   -it npm-filter:latest \
		   bash -c "$npm_filter_command --output_dir results"
rm -r local_mount
