# npm-filter configuration file
The configuration file is a JSON, organized by stages of npm-filter analysis. 
The stages are as follows:
* `install`: package installation. Users can specify:
  * `timeout`: number of millisections after which, if the install is not complete, the process bails and is considered timed out
  * `do_install`: if false, skip the install stage
* `dependencies`: package dependency tracking (this is the libraries the current package depends on, both directly and transitively). Users can specify:
  * `track_deps`: if true, this specifies to compute the package dependencies
  * `include_dev_deps`: if true, this specifies to include the `devDependencies` in the dependency computation
  * `timeout`: timeout in milliseconds
* `build`: package compile/build stage. Users can specify: 
  * `tracked_build_commands`: a list of build commands to test (any npm script with one of these commands as a substring will be tested). Any command not in this list will not be tested for the build stage.
  * `timeout`: timeout in milliseconds, per build command
  * `track_build`: if false, skip the build stage
* `test`: package test stage. Users can specify:
  * `track_tests`: if true, then the tool will run this testing diagnostic stage
  * `tracked_test_commands`: a list of test commands to test (any npm script with one of these commands as a substring will be tested). Any command not in this list will not be tested for the test stage.
  * `timeout`: timeout in milliseconds, per test command
  * `test_verbose_all_output`: an object with two fields to configure the "verbose" test tracking option: here, output and some metrics (runtime, pass/fail, etc) for each test is output to a specified file. Note that currently we only support this option for the `jest` and `mocha` test infras. 
  	* `do_verbose_tracking`: if true, do this verbose test tracking
	* `verbose_json_output_file`: name of the file to which to save this verbose output
* `meta_info`: any analysis-level configurations. Users can specify:
  * `VERBOSE_MODE`: if true, then the output JSON file will include the full output of all the commands run. Mainly for debugging.
  * `ignored_commands`: commands to ignore: if these are present in the npm script name, then they are not run even if they otherwise fall into a category of commands to run (mainly used to exclude any interactive-mode commands, such as tests with `watch`)
  * `ignored_substrings`: commands to ignore: if these strings are present in the command string itself, then these npm scripts are not run (same as `ignored_commands`, but for the command strings instead of the npm script names)
  * `rm_after_cloning`: if true, delete the package source code after the tool is done running. Strongly recommended if running over a large batch of packages.
  * `scripts_over_code`: list of paths to script files to run over the package source code. Note that these paths are relative to the location of **the config file**.
  * `QL_queries`: list of paths to QL query files to run over the package source code. Like the scripts, these paths are relative to the location of the config file.
  * `custom_setup_scripts`: list of paths to script files to run over the package code after cloning, but before any of the stages of `npm-filter` are actually run. Commonly used to replace the default install stage (i.e., set `do_install` to `false`). Like all the other scripts, these paths are relative to the location of the config file.

Users can customize any of the configuration fields, by providing a JSON file with the desired fields modified.
Default values are used for any fields not specified.

As a demonstrative example, the default configuration is included below.
```
{
	"install": {
		"timeout": 1000,
		"do_install": true
	},
	"dependencies": {
		"track_deps": false,
		"include_dev_deps": false
	},
	"build": {
		"track_build": true,
		"tracked_build_commands": ["build", "compile", "init"],
		"timeout": 1000
	},
	"test": {
		"track_tests": true,
		"test_verbose_all_output": {
			"do_verbose_tracking": false,
			"verbose_json_output_file": "verbose_test_report.json"
		},
		"tracked_test_commands": ["test", "unit", "cov", "ci", "integration", "lint", "travis", "e2e", "bench",
								  "mocha", "jest", "ava", "tap", "jasmine"],
		"timeout": 1000
	},
	"meta_info": {
		"VERBOSE_MODE": false,
		"ignored_commands": ["watch", "debug"],
		"ignored_substrings": ["--watch", "nodemon"],
		"rm_after_cloning": false,
		"scripts_over_code": [ ],
		"QL_queries": [ ],
		"custom_setup_scripts": [ ]
	}
}
```

## Infrastructures tracked
npm-filter is configured to track the following infrastructures:
* Testing infrastructures: mocha, jest, jasmine, tap, lab, ava, gulp. \
  Any test commands that run other infrastructures (such as custom node scripts) will still be parsed, but whether or not the correct number of passing/failing tests is determined depends on the shape of the output.
* Linters: eslint, tslint, xx, standard, prettier, gulp lint
* Coverage tools: istanbul, nyc, coveralls, c8

If you have another infrastructure you'd like support for, you can send an email with a request, or add it yourself and submit a PR. [This is the relevant code](https://github.com/emarteca/npm-filter/blob/master/src/test_JS_repo_lib.py#L144) that you'd need to extend.
