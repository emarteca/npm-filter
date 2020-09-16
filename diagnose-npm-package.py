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

VERBOSE_MODE = False
TRACKED_TEST_COMMANDS = ["test", "unit", "cov", "ci", "integration", "lint"]
IGNORED_COMMANDS = ["watch"]
TRACKED_BUILD_COMMANDS = ["build", "compile"]

logging.getLogger('scrapy').propagate = False

def run_command( command):
	process = subprocess.Popen( command.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	return( error, output, process.returncode)

def run_installation( pkg_json):
	manager = ""

	# if there is a yarn lock file use yarn
	# if there is a package-lock, use npm
	# if there is neither, try npm first, and if that fails use yarn
	if os.path.exists( "yarn.lock"):
		print("yarn detected -- installing using yarn")
		manager = "yarn "
		error, output, retcode = run_command( "yarn")
	elif os.path.exists( "package-lock.json"):
		print("package-lock detected -- installing using npm")
		manager = "npm run "
		error, output, retcode = run_command( "npm install")
	else:
		print( "No installer detected -- trying npm")
		manager = "npm run "
		error, output, retcode = run_command( "npm install")
		if retcode != 0:
			print( "No installer detected -- tried npm, error, now trying yarn")
			print(error)
			manager = "yarn "
			error, output, retcode = run_command( "yarn")
	return( (manager, retcode))

def run_build( manager, pkg_json):
	retcode = 0
	build_scripts = [b for b in pkg_json["scripts"].keys() if not set([ b.find(b_com) for b_com in TRACKED_BUILD_COMMANDS]) == {-1}]
	build_scripts = [b for b in build_scripts if set([b.find(ig_com) for ig_com in IGNORED_COMMANDS]) == {-1}]
	print("Trying build commands: ") 
	print(build_scripts)
	for b in build_scripts:
		print("Running: " + manager + b)
		error, output, retcode = run_command( manager + b)
		if retcode != 0 and build_scripts.count(b) < 2:
			print("ERROR running command: " + b)
			build_scripts += [b] # re-add it onto the end of the list, and try running it again after the other build commands
	return( retcode)

def run_tests( manager, pkg_json):
	test_scripts = [t for t in pkg_json["scripts"].keys() if not set([ t.find(t_com) for t_com in TRACKED_TEST_COMMANDS]) == {-1}]
	test_scripts = [t for t in test_scripts if set([t.find(ig_com) for ig_com in IGNORED_COMMANDS]) == {-1}]
	print("Trying test commands: ") 
	print(test_scripts)
	test_info = {}
	for t in test_scripts:
		print("Running: " + manager + t)
		error, output, retcode = run_command( manager + t)
		test_info[t] = TestInfo( (retcode == 0), error, output, manager)
		test_info[t].set_test_command( pkg_json["scripts"][t])
		test_info[t].compute_test_infras()
		test_info[t].compute_test_stats()
		print( test_info[t])
		# print( get_test_info(error, output))
	return( retcode, test_info)

def called_in_command( str_comm, command, manager):
	if command.find( str_comm) == 0:
		return( True)
	if command.find( "&&" + str_comm) > -1 or command.find( "&& " + str_comm) > -1:
		return( True)
	return( False)

def test_cond_count( test_output, regex_fct, condition, offset):
	results = re.findall( regex_fct(condition), test_output)
	num_cond = 0
	for r in results:
		temp = r.split()
		num_cond += int( temp[temp.index(condition) + offset])  
	return( num_cond)


class TestInfo:
	TRACKED_INFRAS = {
		"mocha": {
			"name": "mocha", 
			"output_regex_fct": [
				lambda condition: r'.*\d+ ' + condition + '.*'
			], 
			"passing": [ ("passing", -1)], 
			"failing": [ ("failing", -1)]
		},
		"jest": {
			"name": "jest", 
			"output_regex_fct": [
				lambda condition: r'Tests:.*\d+ ' + condition
			], 
			"passing": [ ("passed", -1)], 
			"failing": [ ("failed", -1)]
		},
		"jasmine": {
			"name": "jasmine", 
			"output_regex_fct": [], 
			"passing": [], 
			"failing": []
		},
		"tap": {
			"name": "tap", 
			"output_regex_fct": [
				lambda condition: r'# ' + condition + '.*\d+'
			], 
			"passing": [ ("pass", 1)], 
			"failing": [ ("fail", 1)]
		},
		"lab": {
			"name": "lab", 
			"output_regex_fct": [], 
			"passing": [], 
			"failing": []
		},
		"ava": {
			"name": "ava", 
			"output_regex_fct": [
				lambda condition: r'.*\d+ tests? ' + condition
			], 
			"passing": [ ("passed", -2)], 
			"failing": [ ("failed", -2)]
		},
		"node": {
			"name": "CUSTOM INFRA: node", 
			"output_regex_fct": [
				lambda condition: r'.*\d+ ' + condition + '.*', 	# mocha
				lambda condition: r'Tests:.*\d+ ' + condition, 		# jest
				lambda condition: r'# ' + condition + '.*d+',		# tap
				lambda condition: r'.*\d+ tests? ' + condition		# ava
			], 
			"passing": [ ("passing", -1), 
						 ("passed", -1),
						 ("pass", 1),
						 ("passed", -2),], 
			"failing": [ ("failing", -1), 
						 ("failed", -1),
						 ("fail", 1),
						 ("failed", -2),]
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
	def __init__(self, success, error_stream, output_stream, manager):
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
		for infra in self.test_infras:
			for regex_fct in TestInfo.TRACKED_INFRAS[infra]["output_regex_fct"]:
				self.num_passing += sum([test_cond_count( test_output, regex_fct, passing[0], passing[1]) for passing in TestInfo.TRACKED_INFRAS[infra]["passing"]])
				self.num_failing += sum([test_cond_count( test_output, regex_fct, failing[0], failing[1]) for failing in TestInfo.TRACKED_INFRAS[infra]["failing"]])


	def __str__(self):
		to_ret = ""
		if self.success == "ERROR":
			to_ret += "ERROR"
			if VERBOSE_MODE:
				to_ret += "\nError output: " + self.error_stream.decode('utf-8')
		else:
			to_ret += "SUCCESS"
			if self.num_passing is not None and self.num_failing is not None:
				to_ret += "\nPassing tests: " + str(self.num_passing) + "\nFailing tests: " + str(self.num_failing)
		if VERBOSE_MODE:
			to_ret += "\nOutput stream: " + self.output_stream.decode('utf-8')
		if self.test_infras and self.test_infras != []:
			to_ret += "\nTest infras: " + str([TestInfo.TRACKED_INFRAS[infra]["name"] for infra in self.test_infras])
		if self.test_covs and self.test_covs != []:
			to_ret += "\nCoverage testing: " + str(self.test_covs)
		if self.test_lints and self.test_lints != []:
			to_ret += "\nLinter: " + str(self.test_lints)
		return( to_ret)

def diagnose_package( repo_link):
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
		f.close()
	except:
  		print("ERROR reading the package.json. Exiting now.")
  		process.exit(0)

	# first, the install
	(manager, retcode) = run_installation( pkg_json)
	if retcode != 0:
		print("ERROR -- installation failed")
		process.exit(0)

	# now, proceed with the build
	retcode = run_build( manager, pkg_json)
	if retcode != 0:
		print("ERROR -- build failed")
		print("Continuing anyway...")

	# then, the testing
	(retcode, test_info) = run_tests( manager, pkg_json)


	# move back to the original working directory
	os.chdir( cur_dir)


	# exit_code = subprocess.call( [script_name, repo_link, repo_name])

class NPMSpider(scrapy.Spider):
	name = "npm-pkgs"
	
	def __init__(self, packages=None, *args, **kwargs):
		if packages is not None:
			self.packages = packages
		self.start_urls = ['https://www.npmjs.com/package/' + pkg for pkg in self.packages]
		super(NPMSpider, self).__init__(*args, **kwargs)

	def parse(self, response):
		soup = BeautifulSoup(response.body, 'html.parser')
		# print(soup.prettify())
		script = soup.find('script', text=re.compile('window\.__context__'))
		json_text = re.search(r'^\s*window\.__context__\s*=\s*({.*?})\s*$',
		                      script.string, flags=re.DOTALL | re.MULTILINE).group(1)
		data = json.loads(json_text)
		
		num_dependents = data['context']['dependents']['dependentsCount']
		repo_link = data['context']['packument']['repository']

		diagnose_package( repo_link)
		
		filename = 'test.html'
		with open(filename, 'wb') as f:
			f.write(response.body)
		f.close()


process = CrawlerProcess(settings={
	"FEEDS": {
	"items.json": {"format": "json"},
	},
})


argparser = argparse.ArgumentParser(description="Diagnose npm packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='+', help="a package to be diagnosed")
argparser.add_argument("--config", metavar="config_file", type=str, nargs='?', help="path to config file")
args = argparser.parse_args()

config = args.config if args.config else {}

process.crawl(NPMSpider, packages=args.packages)
process.start() # the script will block here until the crawling is finished
