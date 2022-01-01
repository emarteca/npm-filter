# Common output processing

npm-filter produces JSON results files for each package or repo that is analyzed. This directory has a python script that does some common output processing: 
given a directory with results JSON files, this script finds the list of all the analyzed packages/repos for which there were no setup/install errors, and for which there is at least one test command that has >= 1 passing test and no failing tests.

## Usage

The script takes one optional argument: the directory in which to look at results files. If not provided, the current directory is used as a default.
```
# general case
python get_json_results.py [output directory to look for results JSON files in]

# specific case: look at current directory
python get_json_results.py

# specific case: look at another directory (here, the parent directory)
python get_json_results.py ..
```

### Example output
This script generates a list of all the analyzed packages/repos that successfully ran and for which there is at least one test command that has >= 1 passing test and no failing tests.
This list is printed to the console newline-delimited, the repo/package name paired with the relevant test command.

For example, running this script on a directory containing the results of running npm-filter on `body-parser` at SHA `d0a214b3beded8a9cd2dcb51d355f92c9ead81d4
` as given in the working example will produce the following output:
```
Following is a list of all projects with commands meeting the criteria, paired with these commands
('..//body-parser__results.json', ['test'])
```
This means that the `body-parser` package has a test command `test` that has passing test(s) and no failing tests.

## Customization
This script is hardcoded to exclude packages with setup/install errors, and only report packages with a test command that has >= 1 passing test(s) and no failing tests.
It can easily be modified for different search parameters.

### Exclusion of packages
Exclusion of packages is done via a `JSON_filter` JSON object, hardcoded at the beginning of the script. To exclude packages with particular results, simply add the fields in the results JSON you want to exclude to this object.
For example, if you want to additionally exclude packages that have no build commands, then you would extend the `JSON_filter` variable with the `build` field as follows:
```
JSON_filter = { 	
	"setup": { 
		"repo_cloning_ERROR": True,
		"pkg_json_ERROR": True
	},
	"installation": { 
		"ERROR": True 
	},
+	"build": {
+	    "build_script_list": []
+	}
}
```

### Filtering for criteria other than all-passing test commands
The script is hardcoded to only report non-excluded packages for which there is a test command with >= 1 passing test and no failing tests.
To modify this criteria, either modify the `get_passing_test_commands` function or write a new function that reports the criteria you want and call that where `get_passing_test_commands` is called currently.

For example, to get packages that run a linter, you could add the function:
```
def get_successful_linter_commands(json_check): 
	test_dict = json_check.get("testing", {})
	passing_commands = []
	for test_com, test_out in test_dict.items():
		if test_out.get("timed_out", False) or test_out.get("ERROR", False): 
			continue
		if test_out.get("test_linters", []) == []:
			continue
		passing_commands += [test_com]
	return( passing_commands)
```
And then, instead of calling `get_passing_test_commands`, call `get_successful_linter_commands`.
In this case, running the script over the directory with `body-parser__results.json` would yield the output:
```
Following is a list of all projects with commands meeting the criteria, paired with these commands
('..//body-parser__results.json', ['lint'])
```

