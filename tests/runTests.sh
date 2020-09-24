#!/bin/bash

# memfs
if [[ -d TESTING_REPOS/memfs ]]; then
        rm -rf TESTING_REPOS/memfs
fi

git clone https://github.com/streamich/memfs.git TESTING_REPOS/memfs >/dev/null 2>&1
cd TESTING_REPOS/memfs
git checkout 863f373185837141504c05ed19f7a253232e0905 >/dev/null 2>&1
cd ../..

python3 diagnose-npm-package.py --packages memfs --html True >/dev/null 2>&1

pkg_diff=`diff memfs__results.json memfs__results_expected.json`
if [ "$pkg_diff" = "" ]; then
	echo "memfs: test passed"
else
	echo "memfs: test failed"
	echo "memfs failing diff: " $pkg_diff
fi
