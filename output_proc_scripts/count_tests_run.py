import json
import os
import sys

# simple, unrefined script for parsing npm-filter output files
# for the current directory, get all files named *__results.json
# (wildcard represents the project name)
# prints out (Number of tests passing),(Number of tests failing)


# JSON specifying possible errors
# that should be avoided if an input JSON will pass the filter check

JSON_filter = { 	
	"setup": { 
		"repo_cloning_ERROR": True,
		"pkg_json_ERROR": True
	},
	"installation": { 
		"ERROR": True 
	},
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
def get_num_tests_run(json_check): 
	test_dict = json_check.get("testing", {})
	num_passing = 0
	num_failing = 0
	passing_commands = []
	for test_com, test_out in test_dict.items():
		if test_out.get("timed_out", False) or (not test_out.get("RUNS_NEW_USER_TESTS", True)) or test_out.get("ERROR", False): 
			continue
		num_passing += test_out.get("num_passing")
		num_failing += test_out.get("num_failing")
	return [num_passing, num_failing]

output_proc_dir = "."
if len(sys.argv) == 2:
	output_proc_dir = sys.argv[1]
else:
	print("No output directory specified: looking at current directory")

# get all relevant files
all_files = [ output_proc_dir + "/" + fname for fname in os.listdir(output_proc_dir) if fname.find("__results.json") != -1]
passing_files = []
total_passing_tests = 0
total_failing_tests = 0
for file in all_files:
	with open(file) as f:
		json_check = json.load(f)
	proj_name = file[ : file.index("__results.json")]
	if json_contains_issues( json_check, JSON_filter):
		# print(proj_name + " has setup/install errors")
		continue
	num_tests = get_num_tests_run( json_check)
	total_passing_tests += num_tests[0]
	total_failing_tests += num_tests[1]

print(f"{total_passing_tests},{total_failing_tests}")