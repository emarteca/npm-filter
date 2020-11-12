#!/bin/bash

repo_link_file=$1

# you'll probably want to bg this
nohup parallel -j 20 -a $repo_link_file --timeout 600 --joblog job.log python diagnose_github_repo.py --repo_link {} --config QL_output_config.json 
