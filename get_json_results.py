import json
import os

# simple, unrefined script for parsing npm-filter output files
# for the current directory, get all files named *__results.json
# (wildcard represents the project name)
# from this list, filter for projects with specific characteristics


# JSON specifying possible errors
# that should be avoided if an input JSON will pass the filter check

JSON_filter = { 	
	"setup": { 
		"repo_cloning_ERROR": True,
		"pkg_json_ERROR": True
	},
	"installation": { 
		"ERROR": True 
	}
}

# input to the function is a JSON of undesirable elements
# return true if the JSON to be filtered has any of the filter elements
def json_contains_issues(json_check, json_filter):
	contains_issues = False
	for filter_key, filter_val in json_filter.items():
		# recursive case
		if isinstance( filter_val, dict):
			contains_issues = contains_issues or json_contains_issues( json_check.get(filter_key, {}), filter_val)
		# base case
		contains_issues = contains_issues or (json_check.get(filter_key, {}) == filter_val)
	return( contains_issues)

# by default, there needs to be at least one passing test
def get_passing_test_commands(json_check, min_passing=1): 
	test_dict = json_check.get("testing", {})
	passing_commands = []
	for test_com, test_out in test_dict.items():
		if test_out.get("timed_out", False) or (not test_out.get("RUNS_NEW_USER_TESTS", True)) or test_out.get("ERROR", False): 
			continue
		if test_out.get("num_failing", 0) > 0:
			continue
		if test_out.get("num_passing", 0) < min_passing:
			continue
		passing_commands += [test_com]
	return( passing_commands)


# get all relevant files
all_files = [ fname for fname in os.listdir() if fname.find("__results.json") != -1]
passing_files = []
for file in all_files:
	print(file)
	with open(file) as f:
		json_check = json.load(f)
	proj_name = file[ : file.index("__results.json")]
	if json_contains_issues( json_check, JSON_filter):
		print(proj_name + " has setup/install errors")
		continue
	passing_commands = get_passing_test_commands( json_check)
	if len(passing_commands) > 0:
		passing_files += [(file, passing_commands)]
print(passing_files)