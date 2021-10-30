
  
#!/bin/bash

mkdir local_mount
docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount -w /home/npm-filter -it npm-filter:latest
rm -r local_mount