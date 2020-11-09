#!/bin/bash

pkg_name=$1

# script to get repo links for all dependencies of a given package
node get_package_deps.js --package $pkg_name --output_file temp_repos.out
python get_package_repo_link.py --package_file temp_repos.out --good_repo_list_mode True > `echo $pkg_name`_deps_repos.txt
rm temp_repos.out