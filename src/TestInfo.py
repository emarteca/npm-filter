import re
import output_parsing.test_output_proc as TestOutputProc

class TestInfo:
	OUTPUT_CHECKERS = {
		"mocha": 
			{
				"output_regex_fct" : lambda condition: r'.*\d+ ' + condition + '.*',
				"passing": ("passing", -1),
				"failing": ("failing", -1)
			},
		"jest": 
			{
				"output_regex_fct" : lambda condition: r'Tests:.*\d+ ' + condition,
				"passing": ("passed", -1),
				"failing": ("failed", -1)
			},
		"tap": {
				"output_regex_fct" : lambda condition: r'# ' + condition + '.*\d+',
				"passing": ("pass", 1),
				"failing": ("fail", 1)
			},
		"tap_raw": {
				"output_regex_fct" : lambda condition: r'' + condition + ' \d+ - (?!.*time=).*$',
				"passing": (r'^.*(?!not )ok', None), # this "passing" is a regex: count "ok" but not "not ok"
				"failing":  (r'^.*not ok', None)
			},
		"ava": 
		{
			"output_regex_fct": lambda condition: r'.*\d+ tests? ' + condition,
			"passing": ("passed", -2), 
			"failing": ("failed", -2)
		},
		"ava_2": 
			{
				"output_regex_fct" : lambda condition: r'.*\d+ ' + condition + '$',
				"passing": ("passed", -1),
				"failing": ("failed", -1)
			},
	}
	# extra args, their position in the arg list, and any post-processing required
    # post-processing is a function that takes 2 arguments: input file and output file
	VERBOSE_TESTS_EXTRA_ARGS = {
		"jest": {
			"args": " --verbose --json --outputFile=$PLACEHOLDER_OUTPUT_FILE_NAME$",
			"position":  -1,
			"post_processing": TestOutputProc.parse_jest_json_to_csv
		},
		"mocha": {
			"args": " -- --reporter xunit --reporter-option output=$PLACEHOLDER_OUTPUT_FILE_NAME$",
			"position": -1,
			"post_processing": TestOutputProc.parse_mocha_json_to_csv
		}
	}
	TRACKED_INFRAS = {
		"mocha": {
			"name": "mocha", 
			"output_checkers": [ "mocha", "tap" ],
			"verbose_tests_extra_args": [ "mocha" ]
		},
		"jest": {
			"name": "jest", 
			"output_checkers": [ "jest" ],
			"verbose_tests_extra_args": [ "jest" ]
		},
		"jasmine": {
			"name": "jasmine", 
			"output_checkers": [ "mocha" ]
		},
		"tap": {
			"name": "tap", 
			"output_checkers": [ "tap", "tap_raw" ]
		},
		"lab": {
			"name": "lab", 
			"output_checkers": []
		},
		"ava": {
			"name": "ava", 
			"output_checkers": [ "ava", "ava_2" ]
		},
		"gulp": {
			"name": "gulp", 
			"output_checkers": [ "mocha" ]
		},
	}
	TRACKED_COVERAGE = {
		"istanbul": "istanbul -- coverage testing",
		"nyc": "nyc -- coverage testing",
		"coveralls": "coveralls -- coverage testing",
		"c8": "c8 -- coverage testing"
	}
	TRACKED_LINTERS = {
		"eslint": "eslint -- linter",
		"tslint": "tslint -- linter",
		"xx": "xx -- linter",
		"standard": "standard -- linter",
		"prettier": "prettier -- linter",
		"gulp lint": "gulp lint -- linter"
	}

	TRACKED_RUNNERS = [ "node", "babel-node", "grunt", "lerna" ]

	def __init__(self, success, error_stream, output_stream, manager, VERBOSE_MODE):
		self.success = success
		self.error_stream = error_stream
		self.output_stream = output_stream
		self.manager = manager
		# start all other fields as None
		self.test_infras = None
		self.test_covs = None
		self.test_lints = None
		self.nested_test_commands = None
		self.num_passing = None
		self.num_failing = None
		self.timed_out = False
		self.VERBOSE_MODE = VERBOSE_MODE
		self.test_verbosity_output = None

	def set_test_command( self, test_command):
		self.test_command = test_command

	def set_test_verbosity_output( self, verbose_output):
		self.test_verbosity_output = verbose_output

	def get_test_infras_list( test_command, manager):
		test_infras = []
		test_infras += [ ti for ti in TestInfo.TRACKED_INFRAS if called_in_command(ti, test_command, manager) ]
		test_infras += [ ri for ri in TestInfo.TRACKED_RUNNERS if called_in_command(ri, test_command, manager) ]
		return( test_infras)

	def compute_test_infras( self):
		self.test_infras = []
		self.test_covs = []
		self.test_lints = []
		self.nested_test_commands = []
		if self.test_command:
			self.test_infras += TestInfo.get_test_infras_list(self.test_command, self.manager)
			self.test_covs += [ TestInfo.TRACKED_COVERAGE[ti] for ti in TestInfo.TRACKED_COVERAGE if called_in_command(ti, self.test_command, self.manager) ]
			self.test_lints += [ TestInfo.TRACKED_LINTERS[ti] for ti in TestInfo.TRACKED_LINTERS if called_in_command(ti, self.test_command, self.manager) ]
		self.test_infras = list(set(self.test_infras))
		self.test_covs = list(set(self.test_covs))
		self.test_lints = list(set(self.test_lints))
		# TODO: maybe we can also figure it out from the output stream

	def compute_nested_test_commands( self, test_commands):
		# one might think that we should only check the package's own manager
		# however, it's common to mix and match (esp. to run commands with "npm run" even if the package manager is yarn)
		self.nested_test_commands += [ tc for tc in test_commands if called_in_command( "npm run " + tc, self.test_command, self.manager) ]
		self.nested_test_commands += [ tc for tc in test_commands if called_in_command( "yarn " + tc, self.test_command, self.manager) ]

	def compute_test_stats( self):
		if not self.test_infras or self.test_infras == []:
			return
		test_output = self.output_stream.decode('utf-8') + self.error_stream.decode('utf-8')
		ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
		test_output = ansi_escape.sub('', test_output)
		self.num_passing = 0
		self.num_failing = 0
		self.timed_out = (self.error_stream.decode('utf-8') == "TIMEOUT ERROR")
		for infra in self.test_infras:
			output_checker_names = TestInfo.TRACKED_INFRAS.get(infra, {}).get("output_checkers", [])
			if infra in TestInfo.TRACKED_RUNNERS and output_checker_names == []:
				output_checker_names = self.OUTPUT_CHECKERS.keys() # all the checkers
			for checker_name in output_checker_names:
				div_factor = 2 if checker_name == "ava_2" else 1
				checker = self.OUTPUT_CHECKERS[ checker_name]
				self.num_passing += int(test_cond_count( test_output, checker["output_regex_fct"], checker["passing"][0], checker["passing"][1]) / div_factor)
				self.num_failing += int(test_cond_count( test_output, checker["output_regex_fct"], checker["failing"][0], checker["failing"][1]) / div_factor)

	def get_json_rep( self):
		json_rep = {}
		if self.VERBOSE_MODE:
			json_rep["test_debug"] = ""
		if not self.success:
			json_rep["ERROR"] = True
			if self.VERBOSE_MODE:
				json_rep["test_debug"] += "\nError output: " + self.error_stream.decode('utf-8')
		if self.num_passing is not None and self.num_failing is not None:
			json_rep["num_passing"] = self.num_passing
			json_rep["num_failing"] = self.num_failing
		if self.VERBOSE_MODE:
			json_rep["test_debug"] += "\nOutput stream: " + self.output_stream.decode('utf-8')
		if self.test_infras and self.test_infras != []:
			json_rep["test_infras"] = [TestInfo.TRACKED_INFRAS.get(infra, {}).get("name", "Custom Testing: " + infra) for infra in self.test_infras]
		if self.test_covs and self.test_covs != []:
			json_rep["test_coverage_tools"] = self.test_covs
		if self.test_lints and self.test_lints != []:
			json_rep["test_linters"] = self.test_lints
		if self.nested_test_commands and self.nested_test_commands != []:
			json_rep["nested_test_commands"] = self.nested_test_commands
		if "test_infras" not in json_rep:
			json_rep["RUNS_NEW_USER_TESTS"] = False
		if self.test_verbosity_output:
			json_rep["test_verbosity_output"] = self.test_verbosity_output
		json_rep["timed_out"] = self.timed_out
		return( json_rep)

	def __str__(self):
		to_ret = ""
		if not self.success:
			to_ret += "ERROR"
			if self.VERBOSE_MODE:
				to_ret += "\nError output: " + self.error_stream.decode('utf-8')
		else:
			to_ret += "SUCCESS"
		if self.num_passing is not None and self.num_failing is not None:
			to_ret += "\nPassing tests: " + str(self.num_passing) + "\nFailing tests: " + str(self.num_failing)
		if self.VERBOSE_MODE:
			to_ret += "\nOutput stream: " + self.output_stream.decode('utf-8')
		if self.test_infras and self.test_infras != []:
			to_ret += "\nTest infras: " + str([TestInfo.TRACKED_INFRAS[infra]["name"] for infra in self.test_infras])
		if self.test_covs and self.test_covs != []:
			to_ret += "\nCoverage testing: " + str(self.test_covs)
		if self.test_lints and self.test_lints != []:
			to_ret += "\nLinter: " + str(self.test_lints)
		if self.nested_test_commands and self.nested_test_commands != []:
			to_ret += "\nNested test commands: " + str(self.nested_test_commands)
		to_ret += "\nTimed out: " + str(self.timed_out)
		return( to_ret)

def called_in_command( str_comm, command, manager):
	# command ends with command terminator (this list includes \0 end-of-string, 
	# but this is not available to check in Python so we use endswith)
	post_command_chars = [ "" ] if command.endswith(str_comm) else [ " ", "\t", ";"]
	for pcc in post_command_chars:
		check_comm = str_comm + pcc
		if command.find( check_comm) == 0:
			return( True)
		if command.find( "&&" + check_comm) > -1 or command.find( "&& " + check_comm) > -1:
			return( True)
		if command.find( "cross-env NODE_ENV=test " + check_comm) > -1 or command.find( "cross-env NODE_ENV=production " + check_comm) > -1:
			return( True)
		if command.find( "cross-env CI=true " + check_comm) > -1:
			return( True)
		if command.find( "cross-env TZ=utc " + check_comm) > -1:
			return( True)
		if command.find( "opener " + check_comm) > -1:
			return( True)
		if command.find( "gulp " + check_comm) > -1:
			return( True)
		if command.find( "nyc " + check_comm) > -1:
			return( True)
	return( False)

def test_cond_count( test_output, regex_fct, condition, offset):
	ptrn = re.compile( regex_fct(condition), re.MULTILINE)
	results = ptrn.findall( test_output)
	if offset is None:
		return( len( results)) # just count the number of hits, each hit is an individual test (example: tap "ok" vs "not ok")
	num_cond = 0
	for r in results:
		temp = r.split()
		try:
			num_cond += int( temp[temp.index(condition) + offset])  
		except ValueError:
			num_cond += 0
	return( num_cond)