import re
import subprocess
import json
import os

def run_command( commands, timeout=None):
	for command in commands.split(";"):
		try:
			process = subprocess.run( command.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		except subprocess.TimeoutExpired:
			error_string = "TIMEOUT ERROR: for user-specified timeout " + str(timeout) + " seconds"
			error = "TIMEOUT ERROR"
			return( error.encode('utf-8'), error_string.encode('utf-8'), 1) # non-zero return code
	return( process.stderr, process.stdout, process.returncode)

def run_installation( pkg_json, crawler):
	installation_command = ""
	installation_debug = "Running Installation\n"
	manager = ""

	# if there is a yarn lock file use yarn
	# if there is a package-lock, use npm
	# if there is neither, try npm first, and if that fails use yarn
	if os.path.exists( "yarn.lock"):
		installation_debug += "\nyarn detected -- installing using yarn"
		manager = "yarn "
		installation_command = "yarn"
		error, output, retcode = run_command( installation_command, crawler.INSTALL_TIMEOUT)
	elif os.path.exists( "package-lock.json"):
		installation_debug += "\npackage-lock detected -- installing using npm"
		manager = "npm run "
		installation_command = "npm install"
		error, output, retcode = run_command( installation_command, crawler.INSTALL_TIMEOUT)
	else:
		installation_debug += "\nNo installer detected -- trying npm"
		manager = "npm run "
		installation_command = "npm install"
		error, output, retcode = run_command( installation_command, crawler.INSTALL_TIMEOUT)
		if retcode != 0:
			installation_debug += "No installer detected -- tried npm, error, now trying yarn"
			manager = "yarn "
			installation_command = "yarn"
			error, output, retcode = run_command( installation_command, crawler.INSTALL_TIMEOUT)
	return( (manager, retcode, installation_command, installation_debug))

def get_deps():
    deps = []
    for d in os.listdir("node_modules"):
	# if a folder's name starts with '.', ignore it.
        if d[0] == '.':
            continue
	# if a folder's name starts with '@', count subfolders in it.
        if d[0] == '@':
            subFolder = os.path.join("node_modules/", d)
            for f in os.listdir(subFolder):
                deps.append(d + '/' + f)

        else:
            deps.append(d)

    return deps

# note: no timeout option for get_dependencies, so "None" is passed as a default timeout argument to run_command
def get_dependencies( pkg_json, manager, include_dev_deps):
	if pkg_json.get("devDependencies", None) and not include_dev_deps:
		run_command( "rm -r node_modules")
		run_command( "mv package.json TEMP_package.json_TEMP")
		dev_deps = pkg_json["devDependencies"]
		pkg_json["devDependencies"] = {}
		with open("package.json", 'w') as f:
			json.dump( pkg_json, f)
		run_command( "npm install" if manager == "npm run " else manager)
		pkg_json["devDependencies"] = dev_deps
	# get the list of deps, excluding hidden directories
	deps = [] if not os.path.isdir("node_modules") else get_deps()
	# then, reset the deps (if required)
	if pkg_json.get("devDependencies", None) and not include_dev_deps:
		run_command( "rm -r node_modules")
		run_command( "mv TEMP_package.json_TEMP package.json")
		run_command( "npm install" if manager == "npm run " else manager)
	return( deps)


def run_build( manager, pkg_json, crawler):
	build_debug = ""
	build_script_list = []
	retcode = 0
	if len(crawler.TRACKED_BUILD_COMMANDS) == 0:
		return(retcode, build_script_list, build_debug)
	build_scripts = [b for b in pkg_json.get("scripts", {}).keys() if not set([ b.find(b_com) for b_com in crawler.TRACKED_BUILD_COMMANDS]) == {-1}]
	build_scripts = [b for b in build_scripts if set([b.find(ig_com) for ig_com in crawler.IGNORED_COMMANDS]) == {-1}]
	build_scripts = [b for b in build_scripts if set([pkg_json.get("scripts", {})[b].find(ig_sub) for ig_sub in crawler.IGNORED_SUBSTRINGS]) == {-1}]
	for b in build_scripts:
		build_debug += "Running: " + manager + b
		error, output, retcode = run_command( manager + b, crawler.BUILD_TIMEOUT)
		if retcode != 0 and build_scripts.count(b) < 2:
			build_debug += "ERROR running command: " + b
			build_scripts += [b] # re-add it onto the end of the list, and try running it again after the other build commands
		elif retcode == 0:
			build_script_list += [b]
	return( retcode, build_script_list, build_debug)

def run_tests( manager, pkg_json, crawler):
	test_json_summary = {}
	retcode = 0
	if len(crawler.TRACKED_TEST_COMMANDS) == 0:
		return(retcode, test_json_summary)
	test_scripts = [t for t in pkg_json.get("scripts", {}).keys() if not set([ t.find(t_com) for t_com in crawler.TRACKED_TEST_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([t.find(ig_com) for ig_com in crawler.IGNORED_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([pkg_json.get("scripts", {})[t].find(ig_sub) for ig_sub in crawler.IGNORED_SUBSTRINGS]) == {-1}]
	for t in test_scripts:
		print("Running: " + manager + t)
		error, output, retcode = run_command( manager + t, crawler.TEST_TIMEOUT)
		test_info = TestInfo( (retcode == 0), error, output, manager, crawler.VERBOSE_MODE)
		test_info.set_test_command( pkg_json.get("scripts", {})[t])
		test_info.compute_test_infras()
		test_info.compute_nested_test_commands( test_scripts)
		test_info.compute_test_stats()
		# if we're in verbose testing mode (i.e. getting all timing info for each test, etc)
		# then, we rerun the test commands with all the commands for adding verbose_mode to 
		# each of the test infras involved (individually)
		if crawler.TEST_VERBOSE_ALL_OUTPUT:
			# we're gonna be adding our new custom scripts for verbosity testing
			run_command( "mv package.json TEMP_package.json_TEMP")
			verbosity_index = 0
			test_verbosity_output = {}
			for test_infra in test_info.test_infras:
				verbose_test_json = ("" if verbosity_index == 0 else "infra_" + str(verbosity_index) + "_") + crawler.TEST_VERBOSE_OUTPUT_JSON
				infra_verbosity_config = TestInfo.VERBOSE_TESTS_EXTRA_ARGS[test_infra]
				if not infra_verbosity_config: # checks if it's an empty object
					print("TEST VERBOSE MODE: unsupported test infra " + test_infra)
					test_verbosity_output[test_infra] = { "error": True }
					continue
				infra_verbosity_args = infra_verbosity_config.get("args", "")
				infra_verbosity_args_pos = infra_verbosity_config.get("position", -1) # default position is at the end
				infra_verbosity_command = instrument_test_command_for_verbose(test_info.test_command, test_infra, infra_verbosity_args, 
																				verbose_test_json, infra_verbosity_args_pos)
				verbosity_script_name = "instrumented_verbosity_command_" + str(verbosity_index)
				pkg_json["scripts"][verbosity_script_name] = infra_verbosity_command
				with open("package.json", 'w') as f:
					json.dump( pkg_json, f)
				print("Running verbosity: " + manager + infra_verbosity_command)
				verb_error, verb_output, verb_retcode = run_command( manager + verbosity_script_name, crawler.TEST_TIMEOUT)
				verbosity_index += 1
				# get the output
				test_verbosity_infra = {}
				test_verbosity_infra["command"] = infra_verbosity_command
				test_verbosity_infra["output_files"] = verbose_test_json
				if crawler.VERBOSE_MODE:
					test_verbosity_infra["test_debug"] = "\nError output: " + verb_error.decode('utf-8') \
														 + "\nOutput stream: " + verb_output.decode('utf-8')
				test_verbosity_output[test_infra] = test_verbosity_infra
			test_info.set_test_verbosity_output(test_verbosity_output)
			# put the package.json back
			run_command( "mv TEMP_package.json_TEMP package.json")
		test_json_summary[t] = test_info.get_json_rep()
	return( retcode, test_json_summary)

def instrument_test_command_for_verbose(test_script, test_infra, infra_verbosity_args, verbose_test_json, infra_verbosity_args_pos):
	# replace the output file name with the custom output filename
	# add an index to the filename for the 2nd,+ time the filename shows up
	# so as to avoid overwriting the files
	num_files = 0
	new_infra_verbosity_args = ""
	for i, sub in enumerate(infra_verbosity_args.split("$PLACEHOLDER_OUTPUT_FILE_NAME$")):
		# not the file name
		if sub != "": 
			new_infra_verbosity_args += sub
		else:
			new_infra_verbosity_args += ("" if num_files == 0 else ("out_" + str(num_files) + "_")) + verbose_test_json 
			num_files += 1
	infra_verbosity_args = new_infra_verbosity_args
	# split into sub-commands
	command_split_chars = [ "&&", ";"]
	infra_calls = test_script.split(test_infra)
	instrumented_test_command = []
	for i, infra_call in enumerate(infra_calls):
		# if the current call is empty string and the next is non-empty
		# then this is the call to the testing infra and the next is the arguments 
		# so, skip this one
		# if there are no args (i.e. no next non-empty string), then just instrument this one
		if infra_call == "" and i < len(infra_calls) - 1 and infra_calls[i + 1] != "":
			instrumented_test_command += [ "" ]
			continue
		# if the first call is non-empty, then it's pre-test-infra and we skip it too
		elif infra_call != "" and i == 0:
			instrumented_test_command += [ "" ]
			continue
		# get the arguments, splitting off from any other non-test commands that might be
		# in this command (note: we know all the commands started with test_infra)
		end_command_pos = re.search(r'|'.join(command_split_chars), infra_call)
		end_command_pos = end_command_pos.start() if not end_command_pos is None else -1
		sub_command_args = (infra_call[0:end_command_pos] if end_command_pos > -1 else infra_call).split(" ")
		if infra_verbosity_args_pos != -1:
			sub_command_args.insert(infra_verbosity_args_pos, infra_verbosity_args)
		else:
			sub_command_args.append(infra_verbosity_args)
		# rebuild the command, re-attaching any extra sub-commands
		instrumented_test_command += [ " ".join(sub_command_args) + (infra_call[end_command_pos:] if end_command_pos > -1 else "") ]
	return(test_infra.join(instrumented_test_command))
	

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
	VERBOSE_TESTS_EXTRA_ARGS = {
		"jest": {
			"args": " --verbose --json --outputFile=$PLACEHOLDER_OUTPUT_FILE_NAME$",
			"position":  -1,
			"post_processing": None
		},
		"mocha": {
			"args": " -- --reporter xunit --reporter-option output=$PLACEHOLDER_OUTPUT_FILE_NAME$",
			"position": -1,
			"post_processing": None #TODO change this to the xml-to-json parser
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

	TRACKED_RUNNERS = [ "node", "babel-node", "grunt" ]

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

	def compute_test_infras( self):
		self.test_infras = []
		self.test_covs = []
		self.test_lints = []
		self.nested_test_commands = []
		if self.test_command:
			self.test_infras += [ ti for ti in TestInfo.TRACKED_INFRAS if called_in_command(ti, self.test_command, self.manager) ]
			self.test_infras += [ ri for ri in TestInfo.TRACKED_RUNNERS if called_in_command(ri, self.test_command, self.manager) ]
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

def on_diagnose_exit( json_out, crawler, cur_dir, repo_name):
	# move back to the original working directory
	if repo_name != "":
		os.chdir( cur_dir)
		if crawler.RM_AFTER_CLONING:
			run_command( "rm -rf TESTING_REPOS/" + repo_name)
	return( json_out)

def diagnose_package( repo_link, crawler, commit_SHA=None):
	json_out = {}

	repo_name = ""
	cur_dir = os.getcwd()
	try: 
		repo_name = repo_link[len(repo_link) - (repo_link[::-1].index("/")):]
	except: 
		print("ERROR cloning the repo -- malformed repo link. Exiting now.")
		json_out["setup"] = {}
		json_out["setup"]["repo_cloning_ERROR"] = True
		return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))

	print("Diagnosing: " + repo_name + " --- from: " + repo_link)

	if not os.path.isdir("TESTING_REPOS"):
		os.mkdir("TESTING_REPOS")
	os.chdir("TESTING_REPOS")

	# first step: cloning the package's repo

	# if the repo already exists, dont clone it
	if not os.path.isdir( repo_name):
		print( "Cloning package repository")
		error, output, retcode = run_command( "git clone " + repo_link)
		if retcode != 0:
			print("ERROR cloning the repo. Exiting now.")
			json_out["setup"] = {}
			json_out["setup"]["repo_cloning_ERROR"] = True
			return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	else:
		print( "Package repository already exists. Using existing directory: " + repo_name)
	

	# move into the repo and begin testing
	os.chdir( repo_name)

	# checkout the specified commit if needed
	if commit_SHA:
		print("Checking out specified commit: " + commit_SHA)
		error, output, retcode = run_command( "git checkout " + commit_SHA)
		if retcode != 0:
			print("ERROR checking out specified commit. Exiting now.")
			json_out["setup"] = {}
			json_out["setup"]["repo_commit_checkout_ERROR"] = True
			return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	

	pkg_json = None
	try:
		with open('package.json') as f:
			pkg_json = json.load(f)
	except:
		print("ERROR reading the package.json. Exiting now.")
		json_out["setup"] = {}
		json_out["setup"]["pkg_json_ERROR"] = True
		return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))

	# first, the install
	manager = ""
	if crawler.DO_INSTALL:
		(manager, retcode, installer_command, installer_debug) = run_installation( pkg_json, crawler)
		json_out["installation"] = {}
		json_out["installation"]["installer_command"] = installer_command
		if crawler.VERBOSE_MODE:
			json_out["installation"]["installer_debug"] = installer_debug
		if retcode != 0:
			print("ERROR -- installation failed")
			json_out["installation"]["ERROR"] = True
			return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	else:
		json_out["installation"] = { "do_install": False }

	if crawler.COMPUTE_DEP_LISTS:
		json_out["dependencies"] = {}
		if not crawler.DO_INSTALL:
			print("Can't get dependencies without installing (do_install: false) -- skipping")
		else:
			print("Getting dependencies")
			dep_list = get_dependencies( pkg_json, manager, crawler.INCLUDE_DEV_DEPS)
			json_out["dependencies"]["dep_list"] = dep_list
			json_out["dependencies"]["includes_dev_deps"] = crawler.INCLUDE_DEV_DEPS

	# now, proceed with the build
	if crawler.TRACK_BUILD:
		json_out["build"] = {}
		if not crawler.DO_INSTALL:
			print("Can't do build without installing (do_install: false) -- skipping")
		else:
			(retcode, build_script_list, build_debug) = run_build( manager, pkg_json, crawler)
			json_out["build"]["build_script_list"] = build_script_list
			if crawler.VERBOSE_MODE:
				json_out["build"]["build_debug"] = build_debug
			if retcode != 0:
				print("ERROR -- build failed. Continuing anyway...")
				json_out["build"]["ERROR"] = True
	else:
		json_out["build"] = { "track_build": False }

	# then, the testing
	if crawler.TRACK_TESTS:
		json_out["testing"] = {}
		if not crawler.DO_INSTALL:
			print("Can't run tests without installing (do_install: false) -- skipping")
		else:
			(retcode, test_json_summary) = run_tests( manager, pkg_json, crawler)
			json_out["testing"] = test_json_summary
	else:
		json_out["testing"] = { "track_tests": False }

	if crawler.SCRIPTS_OVER_CODE != []:
		json_out["scripts_over_code"] = {}
		for script in crawler.SCRIPTS_OVER_CODE:
			print("Running script over code: " + script)
			json_out["scripts_over_code"][script] = {}
			error, output, retcode = run_command( script)
			script_output = output.decode('utf-8') + error.decode('utf-8')
			ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
			script_output = ansi_escape.sub('', script_output)
			json_out["scripts_over_code"][script]["output"] = script_output
			if retcode != 0:
				json_out["scripts_over_code"][script]["ERROR"] = True
	if crawler.QL_QUERIES != []:
		# first, move back out of the repo
		os.chdir(cur_dir)
		json_out["QL_queries"] = {}
		for query in crawler.QL_QUERIES:
			print("Running QL query: " + query)
			json_out["QL_queries"][query] = {}
			# runQuery.sh does the following:
			# - create QL database (with name repo_name)
			# - save the result of the query.ql in repo_name__query__results.csv
			# - clean up: delete the bqrs file
			error, output, retcode = run_command( "src/runQuery.sh TESTING_REPOS/" + repo_name + " " 
													+ repo_name + " " + query + " " + crawler.output_dir)
			if crawler.VERBOSE_MODE:
				query_output = output.decode('utf-8') + error.decode('utf-8')
				ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
				query_output = ansi_escape.sub('', query_output)
				json_out["QL_queries"][query]["output"] = query_output
			if retcode != 0:
				json_out["QL_queries"][query]["ERROR"] = True
		if crawler.RM_AFTER_CLONING:
			run_command( "rm -rf QLDBs/" + repo_name)
		os.chdir( "TESTING_REPOS/" + repo_name)


	return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
