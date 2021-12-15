#!/bin/bash

# if we have a custom version of node, add it to the PATH
if [ -d /opt/nodejs/current/bin ]; then
	PATH=/opt/nodejs/current/bin/:$PATH
fi

# memfs
if [[ -d TESTING_REPOS/memfs ]]; then
        rm -rf TESTING_REPOS/memfs
fi

python3 src/diagnose_github_repo.py --repo_link_and_SHA https://github.com/streamich/memfs 863f373185837141504c05ed19f7a253232e0905 >/dev/null 2>&1

pkg_diff=`diff memfs__results.json memfs__results_expected.json`
if [ "$pkg_diff" = "" ]; then
	echo "memfs: test passed"
else
	echo "memfs: test failed"
	echo "memfs failing diff: " $pkg_diff
fi
