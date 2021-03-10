#!/bin/bash

repo_link_file=$1
config_file=$2

if [ -f $config_file ]; then 
	config_file="QL_output_config.json"
fi

# you'll probably want to bg this
nohup parallel -j 20 -a $repo_link_file --timeout 600 --joblog job.log python3 diagnose_github_repo.py --repo_link {} --config $config_file
