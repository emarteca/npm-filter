# npm-filter
Tool to find npm packages that meet certain criteria, or to determine metrics for specific packages.

Details Forthcoming...

## Running with docker
To be safe, you should probably run any untrusted code in a sandbox.
Since the entire point of this tool is to run code from a set of packages/projects you didn't write, we assume most of this code will fall into the untrusted category.

### Building docker
`docker build -t npm-filter .`

### Sandboxed usage
```
# general use
./runDocker.sh [regular command to run npm-filter]

# example use
./runDocker.sh python3 diagnose_github_repo.py --repo_link https://github.com/jprichardson/node-fs-extra

# another example use
./runDocker.sh python3 diagnose_npm_package.py --packages body-parser

```

### Results
Results from running the docker will be output to a `npm_filter_docker_results` directory generated in the directory you run the container in.


## Running locally
You can also run this locally on your machine.
To do so, you'll need to have the following installed:
* python3 (running as python), with bs4 and scrapy libraries
* git
* npm
* yarn
* node

### Usage
`python diagnose-npm-package.py --packages p1 [p2, ...] [--config config_file] [--output_dir dir_to_output_results_to]`


## TODOs
Things to still get working:
* support for tracking lab and jasmine 
* testing -- make sure it's robust and can deal with potential errors in running packages
* automated scraping for packages (instead of user-specified list)

## Data Analysis
* overall meta analysis: about number of tests in a package, percentage of totally untested packages, percentage of failing packages, etc.
* scraping for particular characteristics (filter for num deps, num passing tests, no failing tests, etc)
