#!/bin/bash

# run npm-filter on a specified repo with verbose, at an optional commit
# output to the "results" directory

# usage: ./run_for_repo_and_config.sh repo_link repo_commit

repo_link=$1
config_file=configs/verbose_only.json
repo_commit=$2

if [ ! -z "$repo_link" ] && [ ! -z "$config_file" ]; then
    if [ ! -z "$repo_commit" ]; then
        python3 src/diagnose_github_repo.py --repo_link_and_SHA $repo_link $repo_commit --config $config_file --output_dir results
    else 
        python3 src/diagnose_github_repo.py --repo_link $repo_link --config $config_file --output_dir results
    fi
fi