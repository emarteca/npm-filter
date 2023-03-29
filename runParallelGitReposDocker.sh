#!/bin/bash

repo_link_file=$1
config_file=$2

if [ ! -f $config_file ] || [ ! $config_file ]; then 
	config_file="configs/QL_output_config.json"
fi

if [ ! -d local_mount ]; then
        mkdir local_mount
fi

# copy config files to a shared volume with the container
if [ ! -d npm_filter_parallel_docker_results ]; then
	mkdir npm_filter_parallel_docker_results
fi
cp $repo_link_file npm_filter_parallel_docker_results/repo_links.txt
cp $config_file npm_filter_parallel_docker_results/config.json

docker run --mount type=bind,source=`pwd`/local_mount,destination=/mount \
                   --volume `pwd`/npm_filter_parallel_docker_results:/home/npm-filter/results \
                   -w /home/npm-filter \
                   -it emarteca/npm-filter:latest \
                   bash -c "nohup parallel -j 20 -a results/repo_links.txt --timeout 600 --joblog job.log python3 src/diagnose_github_repo.py --repo_link {} --config results/config.json --output_dir results"

rm -r local_mount
rm npm_filter_parallel_docker_results/repo_links.txt npm_filter_parallel_docker_results/config.json

