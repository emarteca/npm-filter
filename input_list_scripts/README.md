# Common input generation
npm-filter takes a list of package names or repositories to run over. This list could come from anywhere, but this directory has scripts to automate some of the most common input generation patterns.

## All of a package's direct dependents
A common analysis target is the set of direct dependents of a package -- this is all of the packages that have the specified package as a dependency. We've included a script to automate the computation of the repository links for the direct dependents.
```
# general case:
./get_dep_repos.sh [package_name]

# specific example:
./get_dep_repos.sh memfs

# generates memfs_deps_repos.txt
```
This generates a file `[package_name]_deps_repos.txt` where each line is a repo link for the direct dependents of the specified package.

### Disclaimer
Note that the dependency computation is done using [the npm package `dependent-packages`](https://www.npmjs.com/package/dependent-packages), which is based on an a static version of the npm registry. Therefore, any dependencies computed with this script will be accurate modulo what was present in the version of the npm registry that `dependent-packages` is using.
