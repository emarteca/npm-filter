#!/bin/bash

docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount -w /home/playground -it npm-filter:latest