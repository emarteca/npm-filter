## Testing

The tests run on a specific commit SHA of `memfs`.
This docker also has specific, hardcoded versions of nodejs, npm, and yarn to ensure consistency of results.

```
./prepTestDocker.sh

./runTestDocker.sh
```
