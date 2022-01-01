## Testing

The tests run on a specific commit SHA of `memfs`.
This docker also has specific, hardcoded versions of nodejs, npm, and yarn to ensure consistency of results.

```
# setup the docker container to run the tests
./prepTestDocker.sh

# actually run the tests
./runTestDocker.sh
```

The test docker is constructed using the version of the npm-filter source code in the `src` directory. This test should be run on any updates to the source code, to ensure that the functionality is preserved.

The tests run `src/diagnose_github_repo.py --repo_link_and_SHA https://github.com/streamich/memfs 863f373185837141504c05ed19f7a253232e0905`, inside the constructed test docker. The output JSON file produced is `diff`ed against the expected output file; any difference would case the test to fail.

If the tests pass, you should see the following output:
```
memfs: test passed
```
If the tests fail, then the `diff` will be printed to the terminal.

If you extend the npm-filter functionality, then [the expected JSON output file](https://github.com/emarteca/npm-filter/blob/master/tests/memfs__results_expected.json) will need to be updated accordingly.
