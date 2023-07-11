import re
import subprocess
import json
import os
from TestInfo import *

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

def run_tests( manager, pkg_json, crawler, repo_name, cur_dir="."):
	test_json_summary = {}
	retcode = 0
	if len(crawler.TRACKED_TEST_COMMANDS) == 0:
		return(retcode, test_json_summary)
	test_scripts = [t for t in pkg_json.get("scripts", {}).keys() if not set([ t.find(t_com) for t_com in crawler.TRACKED_TEST_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([t.find(ig_com) for ig_com in crawler.IGNORED_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([pkg_json.get("scripts", {})[t].find(ig_sub) for ig_sub in crawler.IGNORED_SUBSTRINGS]) == {-1}]
	for test_index, t in enumerate(test_scripts):
		test_output_rep = {}
		for test_rep_index in range(crawler.TEST_COMMAND_REPEATS):
			test_rep_id = "" if crawler.TEST_COMMAND_REPEATS == 1 else "testrep_" + str(test_rep_index)
			print("Running rep " + str(test_rep_index) + " of " + str(crawler.TEST_COMMAND_REPEATS - 1) + ": " + manager + t)
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
				test_verbosity_output = {}
				for verbosity_index, test_infra in enumerate(test_info.test_infras):
					verbose_test_json = crawler.output_dir + "/" \
										+ "repo_" + repo_name + "_" \
										+ "test_" + str(test_index) + "_"\
										+ "infra_" + str(verbosity_index) + "_" \
										+ ("" if test_rep_id == "" else test_rep_id + "_") \
										+ crawler.TEST_VERBOSE_OUTPUT_JSON
					infra_verbosity_config = TestInfo.VERBOSE_TESTS_EXTRA_ARGS.get(test_infra)
					if not infra_verbosity_config: # checks if it's an empty object
						print("TEST VERBOSE MODE: unsupported test infra " + test_infra)
						test_verbosity_output[test_infra] = { "error": True }
						continue
					infra_verbosity_args = infra_verbosity_config.get("args", "")
					infra_verbosity_args_pos = infra_verbosity_config.get("position", -1) # default position is at the end
					infra_verbosity_post_proc = infra_verbosity_config.get("post_processing", None)
					infra_verbosity_command, out_files = instrument_test_command_for_verbose(test_info.test_command, test_infra, infra_verbosity_args, 
																					verbose_test_json, infra_verbosity_args_pos)
					verbosity_script_name = "instrumented_verbosity_command_" + str(verbosity_index)
					pkg_json["scripts"][verbosity_script_name] = infra_verbosity_command
					with open("package.json", 'w') as f:
						json.dump( pkg_json, f)
					print("Running verbosity: " + manager + infra_verbosity_command)
					verb_error, verb_output, verb_retcode = run_command( manager + verbosity_script_name, crawler.TEST_TIMEOUT)
					# if there's post-processing to be done
					if not infra_verbosity_post_proc is None:
						for out_file_obj in out_files:
							infra_verbosity_post_proc(out_file_obj["output_file"])
					verbosity_index += 1
					# get the output
					test_verbosity_infra = {}
					test_verbosity_infra["command"] = infra_verbosity_command
					test_verbosity_infra["output_files"] = out_files
					if crawler.VERBOSE_MODE:
						test_verbosity_infra["test_debug"] = "\nError output: " + verb_error.decode('utf-8') \
															+ "\nOutput stream: " + verb_output.decode('utf-8')
					test_verbosity_output[test_infra] = test_verbosity_infra
				test_info.set_test_verbosity_output(test_verbosity_output)
				# put the package.json back
				run_command( "mv TEMP_package.json_TEMP package.json")
			# if we're not doing any repeats then don't make another layer of jsons
			if crawler.TEST_COMMAND_REPEATS == 1:
				test_output_rep = test_info.get_json_rep()
			else:
				test_output_rep[test_rep_id] = test_info.get_json_rep()
		test_json_summary[t] = test_output_rep
	return( retcode, test_json_summary)

def instrument_test_command_for_verbose(test_script, test_infra, infra_verbosity_args, verbose_test_json, infra_verbosity_args_pos):
	# replace the output file name with the custom output filename
	# add an index to the filename for the 2nd,+ time the filename shows up
	# so as to avoid overwriting the files
	num_files = 0
	new_infra_verbosity_args = ""
	output_files = []
	for i, sub in enumerate(infra_verbosity_args.split("$PLACEHOLDER_OUTPUT_FILE_NAME$")):
		out_file_object = { "test_script": test_script, "test_infra": test_infra }
		# not the file name
		if sub != "": 
			new_infra_verbosity_args += sub
		else:
			path_index = verbose_test_json.rfind("/")
			if path_index == -1:
				output_file = "out_" + str(num_files) + "_" + verbose_test_json 
				new_infra_verbosity_args += output_file
				out_file_object["output_file"] = output_file
			else:
				output_file = verbose_test_json[:path_index] + "/out_" + str(num_files) + "_" + verbose_test_json[path_index + 1:]
				print(output_file)
				new_infra_verbosity_args += output_file
				out_file_object["output_file"] = output_file
			output_files += [ out_file_object ]
			num_files += 1
	infra_verbosity_args = new_infra_verbosity_args
	# split into sub-commands
	command_split_chars = [ "&&", ";"]
	infra_calls = test_script.split(test_infra)
	real_calls = []
	for maybe_call in infra_calls:
		# if the last char in the string is not whitespace and not a command delimiter,
		# and it's not the last string in the split
		# then it's a string that is appended to the front of the name of the infra (e.g., "\"jest\"") 
		# and not a call 
		# rebuild it
		if i < len(infra_calls) - 1 and maybe_call != "" and (not maybe_call[-1].isspace()) and (not any([maybe_call.endswith(s) for s in command_split_chars])):
			if len(real_calls) > 0:
				real_calls[-1] += test_infra + maybe_call
				continue
		# if the first char in the string is not whitespace and not a command delimiter,
		# and it's not the first string in the split
		# then it's a string that is appended to the back of the name of the infra (e.g., jest".config.js")
		# and not a call either
		# rebuild it
		if i > 0 and maybe_call != "" and (not maybe_call[0].isspace()) and (not any([maybe_call.startswith(s) for s in command_split_chars])):
			if len(real_calls) > 0:
				real_calls[-1] += test_infra + maybe_call
				continue
		real_calls += [ maybe_call ]
	infra_calls = real_calls
	instrumented_test_command = []
	for i, infra_call in enumerate(infra_calls):
		# if the current call is empty string
		# then this is the call to the testing infra and the next is the arguments 
		# so, skip this one
		# if there are no args (i.e. no next string), then just instrument this one
		if infra_call == "" and i < len(infra_calls) - 1:
			instrumented_test_command += [ "" ]
			continue
		# if the first call is non-empty and there's more than one call, then it's pre-test-infra and we skip it too
		elif len(infra_calls) > 1 and infra_call != "" and i == 0:
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
	return(test_infra.join(instrumented_test_command), output_files)

def on_diagnose_exit( json_out, crawler, cur_dir, repo_name):
	# if we still have the temp package.json, restore it
	if os.path.isfile("TEMP_package.json_TEMP"):
		run_command( "mv TEMP_package.json_TEMP package.json")
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
	
	# diagnose the repo dir
	return( diagnose_repo_name(repo_name, crawler, json_out, cur_dir, commit_SHA=commit_SHA))

def diagnose_local_dir(repo_dir, crawler):
	json_out = {}
	repo_name = ""
	cur_dir = os.getcwd()
	repo_name = repo_dir.split("/")[-1]
	if not os.path.isdir(repo_dir):
		print("ERROR using local directory: " + repo_dir + " invalid directory path")
		json_out["setup"] = {}
		json_out["setup"]["local_dir_ERROR"] = True
		return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	
	print("Diagnosing: " + repo_name + " --- from: " + repo_dir)
	if not os.path.isdir("TESTING_REPOS"):
		os.mkdir("TESTING_REPOS")
	os.chdir("TESTING_REPOS")

	# if the repo already exists, dont clone it
	if not os.path.isdir( repo_name):
		print( "Copying package directory")
		error, output, retcode = run_command( "cp -r " + repo_dir + " " + repo_name)
		if retcode != 0:
			print("ERROR copying the directory. Exiting now.")
			json_out["setup"] = {}
			json_out["setup"]["local_dir_ERROR"] = True
			return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	else:
		print( "Package directory already exists. Using existing directory: " + repo_name)
	# diagnose the repo dir
	return( diagnose_repo_name(repo_name, crawler, json_out, cur_dir))

def diagnose_repo_name(repo_name, crawler, json_out, cur_dir, commit_SHA=None):
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

	manager = ""
	# if there's custom lock files, copy them into the repo (repo is "." since we're in the repo currently)
	if crawler.CUSTOM_LOCK_FILES != []:
		for custom_lock in crawler.CUSTOM_LOCK_FILES:
			run_command("cp " + custom_lock + " .")

	# first, check if there is a custom install
	# this runs custom scripts the same way as the scripts_over_code below; only 
	# difference is it's before the npm-filter run
	if crawler.CUSTOM_SETUP_SCRIPTS != []:
		json_out["custom_setup_scripts"] = {}
		for script in crawler.CUSTOM_SETUP_SCRIPTS:
			print("Running custom setup script script over code: " + script)
			json_out["custom_setup_scripts"][script] = {}
			error, output, retcode = run_command( script)
			script_output = output.decode('utf-8') + error.decode('utf-8')
			ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
			script_output = ansi_escape.sub('', script_output)
			json_out["custom_setup_scripts"][script]["output"] = script_output
			if retcode != 0:
				json_out["custom_setup_scripts"][script]["ERROR"] = True

	# check if the install is done (check if there is a node_modules folder)
	already_installed = os.path.isdir("node_modules")

	# then, the install
	if crawler.DO_INSTALL:
		(new_manager, retcode, installer_command, installer_debug) = run_installation( pkg_json, crawler)
		if manager == "":
			manager = new_manager
		json_out["installation"] = {}
		json_out["installation"]["installer_command"] = installer_command
		if crawler.VERBOSE_MODE:
			json_out["installation"]["installer_debug"] = installer_debug
		if retcode != 0:
			print("ERROR -- installation failed")
			json_out["installation"]["ERROR"] = True
			if not already_installed:
				return( on_diagnose_exit( json_out, crawler, cur_dir, repo_name))
	else:
		json_out["installation"] = { "do_install": False }

	if manager == "": # default the manager to npm if it wasn't already IDd
		manager = "npm run "

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
		if not crawler.DO_INSTALL and not already_installed:
			print("Can't do build without installing (do_install: false and not already installed) -- skipping")
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
		if not crawler.DO_INSTALL and not already_installed:
			print("Can't run tests without installing (do_install: false and not already installed) -- skipping")
		else:
			(retcode, test_json_summary) = run_tests( manager, pkg_json, crawler, repo_name, cur_dir)
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
