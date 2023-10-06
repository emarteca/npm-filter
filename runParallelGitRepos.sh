#!/bin/bash

repo_link_file=$1
config_file=$2
output_dir=$3

if [ ! -f $config_file ]; then 
	config_file="configs/QL_output_config.json"
fi

if [ ! -d $output_dir ]; then
	output_dir=`pwd`
fi

# you'll probably want to bg this
nohup parallel -j 20 -a $repo_link_file --timeout 600 --joblog job.log python3 src/diagnose_github_repo.py --repo_link {} --config $config_file --output_dir $output_dir
