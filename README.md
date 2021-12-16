# npm-filter
Tool to find npm packages that meet certain criteria, or to determine metrics for specific packages.

Details Forthcoming...

Scripts: location is relative to config file
Is the same for QL -- give a QL example

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
./runDocker.sh python3 src/diagnose_github_repo.py --repo_link https://github.com/jprichardson/node-fs-extra

# another example use
./runDocker.sh python3 src/diagnose_npm_package.py --packages body-parser

```

### Docker: where the script needs to read from external files

If you're running `npm-filter` with a custom config file, and running some custom scripts / QL queries over the package code, then you'll need to put these files in a specific folder called `docker_configs`.

Also, anything referenced in the config file must be in this folder, and the locations relative.

For example:
```
./runDocker.sh python3 src/diagnose_github_repo.py --repo_list_file docker_configs/repo_links.txt --config docker_configs/custom_config.json

```
Here we're reading a list of repos from `repo_links.txt` in the `docker_configs` directory.
There's also a custom config file.

Now, if we wanted to run a script over the code, inside `custom_config.json` we'd have:
```
"meta_info": {
		"scripts_over_code": [ "myscript.sh" ],
		"QL_queries": [ "myquery.ql" ]
	}

```
And, `myscript.sh` and `myquery.ql` need to also be in `docker_configs` directory.

Note that running outside of docker you can have different paths to the scripts/queries, but for running in docker they all need to be in the `docker_configs` directory.


### Results
Results from running the docker will be output to a `npm_filter_docker_results` directory generated in the directory you run the container in.

### Parallel execution: also in docker
```
/runParallelGitReposDocker.sh repo_link_file
```
Results are in `npm_filter_parallel_docker_results`.
Note that it's execution in parallel in _one_ docker container, and _not_ parallel docker containers.

## Running locally
You can also run this locally on your machine.
To do so, you'll need to have the following installed:
* python3 (running as python), with bs4 and scrapy libraries
* git
* npm
* yarn
* node

### Usage
`python src/diagnose-npm-package.py --packages p1 [p2, ...] [--config config_file] [--output_dir dir_to_output_results_to]`


## TODOs
Things to still get working:
* support for tracking lab and jasmine 
* testing -- make sure it's robust and can deal with potential errors in running packages
* automated scraping for packages (instead of user-specified list)

## Data Analysis
* overall meta analysis: about number of tests in a package, percentage of totally untested packages, percentage of failing packages, etc.
* scraping for particular characteristics (filter for num deps, num passing tests, no failing tests, etc)
