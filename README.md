# npm-filter 
This tool takes a user-specified set of JavaScript/TypeScript packages, and installs/builds them. \
The primary use case is to automatically determine:
* what the test commands are
* what testing infrastructure is used
* how many passing and failing tests there are

Users can also specify:
* custom scripts, or
* [CodeQL](https://codeql.github.com/) static analyses
to be run over the source code of the package.

## Usage options
This tool can either take packages specified as GitHub repo links, or as npm packages.

### Running over GitHub repo links
To run the tool over GitHub repo links, use the [`diagnose_github_repo.py` script](https://github.com/emarteca/npm-filter/blob/master/src/diagnose_github_repo.py), called as follows:
```
python src/diagnose_github_repo.py 
			[--repo_list_file [rlistfile]] 
			[--repo_link [rlink]] 
			[--repo_link_and_SHA [rlink_and_SHA]] 
			[--config [config_file]]
                        [--output_dir [output_dir]]
```

#### Arguments
All arguments are optional, although the tool will not do anything if no repo links are specified. So effectively, at least one of the three repo-link-specifying arguments must be specified for the tool to run.
* `--repo_list_file [rlistfile]`: a file containing a list of GitHub repo links to be analyzed. \
	Each line of the input file must specify one repo link, with an optional whitespace delimited commit SHA to check the repo out at.
	For example, a valid input file could be:
	```
	https://github.com/expressjs/body-parser 	d0a214b3beded8a9cd2dcb51d355f92c9ead81d4
	https://github.com/streamich/memfs
	```
* `--repo_link [rlink]`: a link to a single GitHub repo to be analyzed, e.g., `https://github.com/expressjs/body-parser`
* `--repo_link_and_SHA [rlink_and_SHA]`: a link to a single GitHub repo to be analyzed, followed by a space-delimited commit SHA to analyze the repo at, e.g., `https://github.com/expressjs/body-parser 	d0a214b3beded8a9cd2dcb51d355f92c9ead81d4`
* `--config [config_file]`: path to a configuration file for the tool (config options explained in [the config file section](#configuration-file)) 
* `--output_dir [output_dir]`: path to a directory in which to output the tool's results files (shape of results are explained in [the output section](#output))

### Running over npm packages
To run the tool over npm packages, use the [`diagnose_npm_package.py` script](https://github.com/emarteca/npm-filter/blob/master/src/diagnose_npm_package.py), called as follows:
```
python src/diagnose_npm_package.py
			--packages [list_of_packages]
			[--config [config_file]]
			[--html [html_file]]
			[--output_dir [output_dir]]
```
The back end of the npm package analyzer is a web scraper: given the name of an npm package, it finds the associated repository link on the npm page so that it can analyze the source code. This tool has some custom middleware to get around the rate limiting on the npm site, but if you are analyzing a large number of packages you will still see a significant performance hit compared to running on the GitHub repos directly. 

#### Arguments
* `--packages [list_of_packages]`: list of npm packages to analyze. This is a required argument, and at least one package must be passed.
* `--config [config_file]`: path to a configuration file for the tool (config options explained in [the config file section](#configuration-file)) 
* `--html [html_file]`: path to an html file that represents the npm page for the package that is specified to be analyzed. This option only works for one package, so if you want to use this option on multiple packages you'll need to call the tool in sequence for each one. 
* `--output_dir [output_dir]`: path to a directory in which to output the tool's results files (shape of results are explained in [the output section](#output)) 

### Configuration file
If you want to customize the behaviour of the tool, you can provide a custom configuration file. All fields in the configuration file are optional -- if not provided, defaults will be used. The [README in the configuration file directory](https://github.com/emarteca/npm-filter/tree/master/configs) goes through all the available options.

### Output
The result of all the package diagnostics are output to a JSON file. The layout of the output is similar to that of the configuration file. 
The output is organized into the following top-level fields in the JSON, in order:
* `setup`: an object with fields that are initialized in the presence of different setup errors that prevent the source code from being properly set up. For example, if the repo link is invalid (or if it can't be found on an npm package page), if there is an error checking out the specified commit, or if there is an error loading the `package.json`.
* `installation`: an object listing the installer command for the package, and/or the presence of any errors in installation that prevent the analysis from continuing
* `dependencies`: an object listing the dependencies of the package, if the configuration specified that they should be tracked
* `build`: an object listing the build commands (in order, and if any) for the package, and/or the presence of any errors in the build commands that prevent the analysis from continuing
* `testing`: an object with fields for each of the test commands in the package. The test commands are those specified in the configuration file. \
	For each test command, the tool lists: 
	* if it is a linter or a coverage tool, and if so what tool (`test_linters`, `test_coverage_tools`)
	* if it's not a linter or coverage tool, what testing infrastructure is being used (`test_infras`)
	* whether or not it runs new user tests (this is false in test commands that only call other test commands, or test commands that don't run any tests explicitly (e.g., linters, coverage tools) (`RUNS_NEW_USER_TESTS`)
	* if it runs other test commands, then a list of these commands are included (`nested_test_commands`)
	* whether or not it timed out (`timed_out`)
	* if it does run new user tests, then the number of passing and number of failing tests (`num_passing`, `num_failing`)
* `scripts_over_code`: an object with fields for each of the scripts run over the package source code. For each script, the tool lists its output and if there was an error.
* `QL_queries`: an object with fields for each of the QL queries run over the package source code. For each script, the tool lists the output (if running in verbose mode), and if there was an error.
* `metadata`: an object with fields for some metadata about the package: repository link, commit SHA if one was specified

For example, the output of running `diagnose_github_repo` on `https://github.com/expressjs/body-parser` at commit SHA `d0a214b3beded8a9cd2dcb51d355f92c9ead81d4` with the default configuration file is as follows:
```
{
    "installation": {
        "installer_command": "npm install"
    },
    "build": {
        "build_script_list": []
    },
    "testing": {
        "lint": {
            "test_linters": [
                "eslint -- linter"
            ],
            "RUNS_NEW_USER_TESTS": false,
            "timed_out": false
        },
        "test": {
            "num_passing": 231,
            "num_failing": 0,
            "test_infras": [
                "mocha"
            ],
            "timed_out": false
        },
        "test-ci": {
            "test_coverage_tools": [
                "nyc -- coverage testing"
            ],
            "RUNS_NEW_USER_TESTS": false,
            "timed_out": false
        },
        "test-cov": {
            "test_coverage_tools": [
                "nyc -- coverage testing"
            ],
            "RUNS_NEW_USER_TESTS": false,
            "timed_out": false
        }
    },
    "scripts_over_code": {},
    "QL_queries": {},
    "metadata": {
        "repo_link": "https://github.com/expressjs/body-parser",
        "repo_commit_SHA": "d0a214b3beded8a9cd2dcb51d355f92c9ead81d4"
    }
}
```

#### QL Query output
The output of each QL query is saved to a CSV file in the same directory as the JSON output, named `[package name]__[query name]__results.csv`. For example, if you run a query `myQuery.ql` over `body-parser`, the query results file will be `body-parser__myQuery__results.csv`.

### Running with docker
To be safe, you should probably run any untrusted code in a sandbox.
Since the entire point of this tool is to run code from a set of packages/projects you didn't write, we assume most of this code will fall into the untrusted category.
We host the docker container [on DockerHub](https://hub.docker.com/r/emarteca/npm-filter); if you edit the package source code and want to run your version in a docker container, we have included the docker build command below.

#### Building docker (if you've updated the npm-filter source code)
Note: you don't need to do this if you're using npm-filter out of the box. 
In that case, you'll pull directly from DockerHub.
`docker build -t npm-filter .`

#### Sandboxed usage
```
# general use
./runDocker.sh [regular command to run npm-filter]

# example use
./runDocker.sh python3 src/diagnose_github_repo.py --repo_link https://github.com/jprichardson/node-fs-extra

# another example use
./runDocker.sh python3 src/diagnose_npm_package.py --packages body-parser

```

#### Docker: where the script needs to read from external files

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


#### Results
Results from running the docker will be output to a `npm_filter_docker_results` directory generated in the directory you run the container in.

#### Parallel execution: also in docker
```
./runParallelGitReposDocker.sh repo_link_file
```
Results are in `npm_filter_parallel_docker_results`.
Note that it's execution in parallel in _one_ docker container, and _not_ parallel docker containers.

### Running locally
You can also run this locally on your machine.
To do so, you'll need to have the following installed:
* python3 (running as python), with bs4 and scrapy libraries
* git
* npm
* yarn
* node


## Example uses
Examples of common usages:

### Specifying packages as github repos
```
# running on a single repo
python src/diagnose_github_repo.py --repo_link https://github.com/expressjs/body-parser

# running on a single repo with a custom config file
python src/diagnose_github_repo.py --repo_link https://github.com/expressjs/body-parser --config my_config.json

# running on a single repo at a specific SHA
python3 src/diagnose_github_repo.py --repo_link_and_SHA https://github.com/streamich/memfs 863f373185837141504c05ed19f7a253232e0905

# running on one repo from a link, and a list of repos from a file
python src/diagnose_github_repo.py --repo_link https://github.com/expressjs/body-parser --repo_list_file repo_links.txt
```

### Specifying packages via npm package names
```
# running on a single package
python src/diagnose_npm_package.py --packages body-parser

# running on multiple packages
python src/diagnose_npm_package.py --packages body-parser memfs fs-extra

# running on multiple packages with a custom output directory (the parent directory)
python src/diagnose_npm_package.py --packages body-parser memfs --output_dir ..
```

## Common input generation

npm-filter takes as input a list of package names or repositories to run over. The [`input_list_scripts` directory](https://github.com/emarteca/npm-filter/tree/master/input_list_scripts) contains scripts for common input generation strategies.

## Common output processing

npm-filter produces JSON results files for each package or repo that is analyzed. The [`output_proc_scripts` directory](https://github.com/emarteca/npm-filter/tree/master/output_proc_scripts) constains scripts for common output processing.

## Running tests

Instructions on setting up and running the npm-filter test suite are included [in the `tests` directory](https://github.com/emarteca/npm-filter/blob/master/tests).

