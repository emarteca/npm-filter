import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from bs4 import BeautifulSoup
import json
import re
import subprocess
import os
import logging
import argparse

logging.getLogger('scrapy').propagate = False

def run_command( command, timeout=None):
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

# note: no timeout option for get_dependencies, so "None" is passed as a default timeout argument to run_command
def get_dependencies( pkg_json, manager, include_dev_deps):
	if pkg_json["devDependencies"] and not include_dev_deps:
		run_command( "rm -r node_modules")
		run_command( "mv package.json TEMP_package.json_TEMP")
		dev_deps = pkg_json["devDependencies"]
		pkg_json["devDependencies"] = {}
		with open("package.json", 'w') as f:
			json.dump( pkg_json, f)
		run_command( manager + (" install" if manager == "npm run " else ""))
		pkg_json["devDependencies"] = dev_deps
	# get the list of deps, excluding hidden directories
	deps = [d for d in os.listdir("node_modules") if not d[0] == "."] 
	# then, reset the deps (if required)
	if pkg_json["devDependencies"] and not include_dev_deps:
		run_command( "rm -r node_modules")
		run_command( "mv TEMP_package.json_TEMP package.json")
		run_command( manager + (" install" if manager == "npm run " else ""))
	return( deps)


def run_build( manager, pkg_json, crawler):
	retcode = 0
	build_scripts = [b for b in pkg_json["scripts"].keys() if not set([ b.find(b_com) for b_com in crawler.TRACKED_BUILD_COMMANDS]) == {-1}]
	build_scripts = [b for b in build_scripts if set([b.find(ig_com) for ig_com in crawler.IGNORED_COMMANDS]) == {-1}]
	build_debug = ""
	build_script_list = []
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
	test_scripts = [t for t in pkg_json["scripts"].keys() if not set([ t.find(t_com) for t_com in crawler.TRACKED_TEST_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([t.find(ig_com) for ig_com in crawler.IGNORED_COMMANDS]) == {-1}]
	test_json_summary = {}
	for t in test_scripts:
		print("Running: " + manager + t)
		error, output, retcode = run_command( manager + t, crawler.TEST_TIMEOUT)
		test_info = TestInfo( (retcode == 0), error, output, manager, crawler.VERBOSE_MODE)
		test_info.set_test_command( pkg_json["scripts"][t])
		test_info.compute_test_infras()
		test_info.compute_test_stats()
		# print( test_info[t])
		# print( get_test_info(error, output))
		test_json_summary[t] = test_info.get_json_rep()
	return( retcode, test_json_summary)

def called_in_command( str_comm, command, manager):
	if command.find( str_comm) == 0:
		return( True)
	if command.find( "&&" + str_comm) > -1 or command.find( "&& " + str_comm) > -1:
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
	TRACKED_INFRAS = {
		"mocha": {
			"name": "mocha", 
			"output_checkers": [
				{
					"output_regex_fct" : lambda condition: r'.*\d+ ' + condition + '.*',
					"passing": ("passing", -1),
					"failing": ("failing", -1)
				}
			]
		},
		"jest": {
			"name": "jest", 
			"output_checkers": [
				{
					"output_regex_fct" : lambda condition: r'Tests:.*\d+ ' + condition,
					"passing": ("passed", -1),
					"failing": ("failed", -1)
				}
			]
		},
		"jasmine": {
			"name": "jasmine", 
			"output_checkers": []
		},
		"tap": {
			"name": "tap", 
			"output_checkers": [
				{
					"output_regex_fct" : lambda condition: r'# ' + condition + '.*\d+',
					"passing": ("pass", 1),
					"failing": ("fail", 1)
				},
				{
					"output_regex_fct" : lambda condition: r'' + condition + ' \d+ - (?!.*time=).*$',
					"passing": (r'^.*(?!not )ok', None), # this "passing" is a regex: count "ok" but not "not ok"
					"failing":  ("not ok", None)
				}
			]
		},
		"lab": {
			"name": "lab", 
			"output_checkers": []
		},
		"ava": {
			"name": "ava", 
			"output_checkers": [
				{
					"output_regex_fct": lambda condition: r'.*\d+ tests? ' + condition,
					"passing": ("passed", -2), 
					"failing": ("failed", -2)
				}
			]
		},
		"node": {
			"name": "CUSTOM INFRA: node", 
			"output_checkers": [
				{ # mocha
					"output_regex_fct" : lambda condition: r'.*\d+ ' + condition + '.*',
					"passing": ("passing", -1),
					"failing": ("failing", -1)
				},
				{ # jest
					"output_regex_fct" : lambda condition: r'Tests:.*\d+ ' + condition,
					"passing": ("passed", -1),
					"failing": ("failed", -1)
				}, 
				{ # tap
					"output_regex_fct" : lambda condition: r'# ' + condition + '.*\d+',
					"passing": ("pass", 1),
					"failing": ("fail", 1)
				},
				{ # also tap
					"output_regex_fct" : lambda condition: r'' + condition + ' \d+ - (?!.*time=).*$',
					"passing": (r'^.*(?!not )ok', None), # this "passing" is a regex: count "ok" but not "not ok"
					"failing":  ("not ok", None)
				},
				{ # ava
					"output_regex_fct": lambda condition: r'.*\d+ tests? ' + condition,
					"passing": ("passed", -2), 
					"failing": ("failed", -2)
				}
			]
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
		"standard": "standard -- linter"
	}
	def __init__(self, success, error_stream, output_stream, manager, VERBOSE_MODE):
		self.success = success
		self.error_stream = error_stream
		self.output_stream = output_stream
		self.manager = manager
		# start all other fields as None
		self.test_infras = None
		self.test_covs = None
		self.test_lints = None
		self.num_passing = None
		self.num_failing = None
		self.timed_out = False
		self.VERBOSE_MODE = VERBOSE_MODE

	def set_test_command( self, test_command):
		self.test_command = test_command

	def compute_test_infras( self):
		self.test_infras = []
		self.test_covs = []
		self.test_lints = []
		if self.test_command:
			self.test_infras += [ ti for ti in TestInfo.TRACKED_INFRAS if called_in_command(ti, self.test_command, self.manager) ]
			self.test_covs += [ TestInfo.TRACKED_COVERAGE[ti] for ti in TestInfo.TRACKED_COVERAGE if called_in_command(ti, self.test_command, self.manager) ]
			self.test_lints += [ TestInfo.TRACKED_LINTERS[ti] for ti in TestInfo.TRACKED_LINTERS if called_in_command(ti, self.test_command, self.manager) ]
		self.test_infras = list(set(self.test_infras))
		self.test_covs = list(set(self.test_covs))
		self.test_lints = list(set(self.test_lints))
		# TODO: maybe we can also figure it out from the output stream

	def compute_test_stats( self):
		if not self.test_infras or self.test_infras == []:
			return
		test_output = self.output_stream.decode('utf-8') + self.error_stream.decode('utf-8')
		self.num_passing = 0
		self.num_failing = 0
		self.timed_out = (self.error_stream.decode('utf-8') == "TIMEOUT ERROR")
		for infra in self.test_infras:
			for checker in TestInfo.TRACKED_INFRAS[infra]["output_checkers"]:
				self.num_passing += test_cond_count( test_output, checker["output_regex_fct"], checker["passing"][0], checker["passing"][1])
				self.num_failing += test_cond_count( test_output, checker["output_regex_fct"], checker["failing"][0], checker["failing"][1])

	def get_json_rep( self):
		json_rep = {}
		if self.VERBOSE_MODE:
			json_rep["test_debug"] = ""
		if self.success == "ERROR":
			json_rep["ERROR"] = True
			if VERBOSE_MODE:
				json_rep["test_debug"] += "\nError output: " + self.error_stream.decode('utf-8')
		else:
			if self.num_passing is not None and self.num_failing is not None:
				json_rep["num_passing"] = self.num_passing
				json_rep["num_failing"] = self.num_failing
		if self.VERBOSE_MODE:
			json_rep["test_debug"] += "\nOutput stream: " + self.output_stream.decode('utf-8')
		if self.test_infras and self.test_infras != []:
			json_rep["test_infras"] = [TestInfo.TRACKED_INFRAS[infra]["name"] for infra in self.test_infras]
		if self.test_covs and self.test_covs != []:
			json_rep["test_coverage_tools"] = self.test_covs
		if self.test_lints and self.test_lints != []:
			json_rep["test_linters"] = self.test_lints
		if "test_infras" not in json_rep:
			json_rep["RUNS_USER_TESTS"] = False
		json_rep["timed_out"] = self.timed_out
		return( json_rep)

	def __str__(self):
		to_ret = ""
		if self.success == "ERROR":
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
		to_ret += "\nTimed out: " + str(self.timed_out)
		return( to_ret)

def diagnose_package( repo_link, crawler):

	json_out = {}

	repo_name = repo_link[len(repo_link) - (repo_link[::-1].index("/")):]
	cur_dir = os.getcwd()

	if not os.path.isdir("TESTING_REPOS"):
		os.mkdir("TESTING_REPOS")
	os.chdir("TESTING_REPOS")

	# first step: cloning the package's repo

	# if the repo already exists, dont clone it
	if not os.path.isdir( repo_name):
		print( "Cloning package repository")
		error, output, retcode = run_command( "git clone " + repo_link)
	else:
		print( "Package repository already exists. Using existing directory: " + repo_name)
	

	# move into the repo and begin testing
	os.chdir( repo_name)

	pkg_json = None
	try:
		with open('package.json') as f:
			pkg_json = json.load(f)
	except:
  		print("ERROR reading the package.json. Exiting now.")
  		process.exit(0)

	# first, the install
	(manager, retcode, installer_command, installer_debug) = run_installation( pkg_json, crawler)
	json_out["installation"] = {}
	json_out["installation"]["installer_command"] = installer_command
	if crawler.VERBOSE_MODE:
		json_out["installation"]["installer_debug"] = installer_debug
	if retcode != 0:
		print("ERROR -- installation failed")
		json_out["installation"]["ERROR"] = True
		return( json_out)

	if crawler.COMPUTE_DEP_LISTS:
		print("Getting dependencies")
		dep_list = get_dependencies( pkg_json, manager, crawler.INCLUDE_DEV_DEPS)
		json_out["dependencies"] = {}
		json_out["dependencies"]["dep_list"] = dep_list
		json_out["dependencies"]["includes_dev_deps"] = crawler.INCLUDE_DEV_DEPS

	# now, proceed with the build
	(retcode, build_script_list, build_debug) = run_build( manager, pkg_json, crawler)
	json_out["build"] = {}
	json_out["build"]["build_script_list"] = build_script_list
	if crawler.VERBOSE_MODE:
		json_out["build"]["build_debug"] = build_debug
	if retcode != 0:
		print("ERROR -- build failed. Continuing anyway...")
		json_out["build"]["ERROR"] = True

	# then, the testing
	if crawler.TRACK_TESTS:
		(retcode, test_json_summary) = run_tests( manager, pkg_json, crawler)
		json_out["testing"] = test_json_summary

	# move back to the original working directory
	os.chdir( cur_dir)

	if crawler.RM_AFTER_CLONING:
		run_command( "rm -rf TESTING_REPOS/" + repo_name)

	return( json_out)


class NPMSpider(scrapy.Spider):
	name = "npm-pkgs"
	VERBOSE_MODE = False
	RM_AFTER_CLONING = False

	INCLUDE_DEV_DEPS = False
	COMPUTE_DEP_LISTS = False
	TRACK_TESTS = True

	TRACKED_TEST_COMMANDS = ["test", "unit", "cov", "ci", "integration", "lint"]
	IGNORED_COMMANDS = ["watch"]
	TRACKED_BUILD_COMMANDS = ["build", "compile"]

	# timeouts for stages, in seconds
	INSTALL_TIMEOUT = 1000
	# note: these are timeouts pers *script* in the stage of the process
	BUILD_TIMEOUT = 1000
	TEST_TIMEOUT = 1000
	
	def __init__(self, packages=None, config_file="", *args, **kwargs):
		if packages is not None:
			self.packages = packages
		self.start_urls = ['https://www.npmjs.com/package/' + pkg for pkg in self.packages]
		self.set_up_config( config_file)
		super(NPMSpider, self).__init__(*args, **kwargs)

	def set_up_config( self, config_file):
		if not os.path.exists(config_file):
			if config_file != "":
				print("Could not find config file: " + config_file + " --- using defaults")
			return

		config_json = {}
		try:
			with open( config_file, 'r') as f:
				config_json = json.loads(f.read())
		except:
			print("Error reading config file: " + config_file + " --- using defaults")

		# now, read the relevant config info from the file
		cf_dict = config_json.get( "meta_info", {})
		self.VERBOSE_MODE = cf_dict.get("VERBOSE_MODE", self.VERBOSE_MODE)
		self.IGNORED_COMMANDS = cf_dict.get( "ignored_commands", self.IGNORED_COMMANDS)
		self.RM_AFTER_CLONING = cf_dict.get( "rm_after_cloning", self.RM_AFTER_CLONING)

		cf_dict = config_json.get( "dependencies", {})
		self.INCLUDE_DEV_DEPS = cf_dict.get("include_dev_deps", self.INCLUDE_DEV_DEPS)
		self.COMPUTE_DEP_LISTS = cf_dict.get("track_deps", self.COMPUTE_DEP_LISTS)

		cf_dict = config_json.get( "install", {})
		self.INSTALL_TIMEOUT = cf_dict.get("timeout", self.INSTALL_TIMEOUT)

		cf_dict = config_json.get( "build", {})
		self.BUILD_TIMEOUT = cf_dict.get("timeout", self.BUILD_TIMEOUT)
		self.TRACKED_BUILD_COMMANDS = cf_dict.get("tracked_build_commands", self.TRACKED_BUILD_COMMANDS)

		cf_dict = config_json.get("test", {})
		self.TEST_TIMEOUT = cf_dict.get("timeout", self.TEST_TIMEOUT)
		self.TRACKED_TEST_COMMANDS = cf_dict.get("tracked_test_commands", self.TRACKED_TEST_COMMANDS)
		self.TRACK_TESTS = cf_dict.get("track_tests", self.TRACK_TESTS)

	def parse(self, response):
		soup = BeautifulSoup(response.body, 'html.parser')
		# print(soup.prettify())
		script = soup.find('script', text=re.compile('window\.__context__'))
		json_text = re.search(r'^\s*window\.__context__\s*=\s*({.*?})\s*$',
		                      script.string, flags=re.DOTALL | re.MULTILINE).group(1)
		data = json.loads(json_text)
		
		num_dependents = data['context']['dependents']['dependentsCount']
		repo_link = data['context']['packument']['repository']
		package_name = data['context']['packument']['name']

		json_results = diagnose_package( repo_link, self)

		json_results["metadata"] = {}
		json_results["metadata"]["package_name"] = package_name
		json_results["metadata"]["repo_link"] = repo_link
		json_results["metadata"]["num_dependents"] = num_dependents
		
		with open(package_name + '__page_data.html', 'wb') as f:
			f.write(response.body)
		with open(package_name + '__results.json', 'w') as f:
			json.dump( json_results, f, indent=4)


process = CrawlerProcess(settings={
	"FEEDS": {
	"items.json": {"format": "json"},
	},
})


argparser = argparse.ArgumentParser(description="Diagnose npm packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='+', help="a package to be diagnosed")
argparser.add_argument("--config", metavar="config_file", type=str, nargs='?', help="path to config file")
args = argparser.parse_args()

config = args.config if args.config else ""

process.crawl(NPMSpider, packages=args.packages, config_file=config)
process.start() # the script will block here until the crawling is finished
