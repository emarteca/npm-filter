#!/bin/bash

if [ ! -d local_mount ]; then
	mkdir local_mount
fi

docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount \
	-it npm-filter:latest \
	bash -c "./runTests.sh"
rm -r local_mount
