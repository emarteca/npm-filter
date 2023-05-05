import json
import re
import subprocess
import os
import argparse
from test_JS_repo_lib import *
import get_repo_links as GetLinks

# expecting links to look like :
# https://github.com/user/reponame [optional commit SHA]
def get_name_from_link(link): 
	# split first on whitespace and take the first word
	# to make sure we ignore the optional commit SHA
	return( link.split()[0].split("/")[-1])

def get_repo_and_SHA_from_repo_link(repo):
	split_res = repo.split()
	commit_SHA = None
	if len(split_res) > 1:
		commit_SHA = split_res[1]
	return(split_res[0], commit_SHA)


class RepoWalker():
	name = "npm-pkgs"
	VERBOSE_MODE = False
	RM_AFTER_CLONING = False
	SCRIPTS_OVER_CODE = []
	QL_QUERIES = []

	DO_INSTALL = True
	INCLUDE_DEV_DEPS = False
	COMPUTE_DEP_LISTS = False
	TRACK_BUILD = True
	TRACK_TESTS = True
	TEST_VERBOSE_ALL_OUTPUT = False
	TEST_VERBOSE_OUTPUT_JSON = "verbose_test_report.json"

	TRACKED_TEST_COMMANDS = ["test", "unit", "cov", "ci", "integration", "lint", "travis", "e2e", "bench", 
							 "mocha", "jest", "ava", "tap", "jasmine"]
	IGNORED_COMMANDS = ["watch", "debug"]
	IGNORED_SUBSTRINGS = ["--watch", "nodemon"]
	TRACKED_BUILD_COMMANDS = ["build", "compile", "init"]

	# timeouts for stages, in seconds
	INSTALL_TIMEOUT = 1000
	# note: these are timeouts per *script* in the stage of the process
	BUILD_TIMEOUT = 1000
	TEST_TIMEOUT = 1000

	QL_CUTOFF = 5 # ignore if there are < 5 results
	
	def __init__(self, config_file="", output_dir = "."):
		self.set_up_config( config_file)
		self.output_dir = os.path.abspath(output_dir)

	def set_repo_links(self, repo_links):
		self.repo_links = repo_links

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
		self.IGNORED_SUBSTRINGS = cf_dict.get( "ignored_substrings", self.IGNORED_SUBSTRINGS)
		self.RM_AFTER_CLONING = cf_dict.get( "rm_after_cloning", self.RM_AFTER_CLONING)
		# script and query file location is relative to the config file
		self.SCRIPTS_OVER_CODE = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "scripts_over_code", self.SCRIPTS_OVER_CODE)]
		self.QL_QUERIES = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "QL_queries", self.QL_QUERIES)]

		cf_dict = config_json.get( "dependencies", {})
		self.INCLUDE_DEV_DEPS = cf_dict.get("include_dev_deps", self.INCLUDE_DEV_DEPS)
		self.COMPUTE_DEP_LISTS = cf_dict.get("track_deps", self.COMPUTE_DEP_LISTS)

		cf_dict = config_json.get( "install", {})
		self.DO_INSTALL = cf_dict.get("do_install", self.DO_INSTALL)
		self.INSTALL_TIMEOUT = cf_dict.get("timeout", self.INSTALL_TIMEOUT)

		cf_dict = config_json.get( "build", {})
		self.TRACK_BUILD = cf_dict.get("track_build", self.TRACK_BUILD)
		self.BUILD_TIMEOUT = cf_dict.get("timeout", self.BUILD_TIMEOUT)
		self.TRACKED_BUILD_COMMANDS = cf_dict.get("tracked_build_commands", self.TRACKED_BUILD_COMMANDS)

		cf_dict = config_json.get("test", {})
		self.TEST_TIMEOUT = cf_dict.get("timeout", self.TEST_TIMEOUT)
		self.TRACKED_TEST_COMMANDS = cf_dict.get("tracked_test_commands", self.TRACKED_TEST_COMMANDS)
		self.TRACK_TESTS = cf_dict.get("track_tests", self.TRACK_TESTS)
		test_verbose_config = cf_dict.get("test_verbose_all_output", {})
		self.TEST_VERBOSE_ALL_OUTPUT = test_verbose_config.get("do_verbose_tracking", self.TEST_VERBOSE_ALL_OUTPUT)
		self.TEST_VERBOSE_OUTPUT_JSON = test_verbose_config.get("verbose_json_output_file", self.TEST_VERBOSE_OUTPUT_JSON)

		cf_dict = config_json.get("QL_output", {})
		self.QL_CUTOFF = cf_dict.get("QL_cutoff", self.QL_CUTOFF)

	def iterate_over_repos( self):
		for repo in self.repo_links:
			[repo_link, commit_SHA] = get_repo_and_SHA_from_repo_link(repo)
			package_name = get_name_from_link( repo_link)
			json_results = diagnose_package( repo_link, self, commit_SHA)
			json_results["metadata"] = {}
			json_results["metadata"]["repo_link"] = repo_link
			# if not None
			if commit_SHA:
				json_results["metadata"]["repo_commit_SHA"] = commit_SHA
			with open(self.output_dir + "/" + package_name + '__results.json', 'w') as f:
				json.dump( json_results, f, indent=4)


argparser = argparse.ArgumentParser(description="Diagnose github repos, from a variety of sources")
argparser.add_argument("--repo_list_file", metavar="rlistfile", type=str, nargs='?', help="file with list of github repo links")
argparser.add_argument("--repo_link", metavar="rlink", type=str, nargs='?', help="single repo link")
argparser.add_argument("--repo_link_and_SHA", metavar="rlink_and_SHA", type=str, nargs='*', help="single repo link, with optional commit SHA")
argparser.add_argument("--config", metavar="config_file", type=str, nargs='?', help="path to config file")
argparser.add_argument("--output_dir", metavar="output_dir", type=str, nargs='?', help="directory for results to be output to")
args = argparser.parse_args()

config = args.config if args.config else ""

output_dir = args.output_dir if args.output_dir else "."

walker = RepoWalker(config_file=config, output_dir=output_dir)

repo_links = []
if args.repo_list_file:
	try:
		repo_links += GetLinks.from_list_of_repos(args.repo_list_file)
	except:
		print("Error reading list of repos file: " + args.repo_list_file + " --- no repos to try")
		repo_links += []


if args.repo_link:
	repo_links += [args.repo_link]

if args.repo_link_and_SHA:
	# repo_link_and_SHA can have an optional commit SHA: if so it's space delimited
	# so we join all the repo_link args into a space-delimited string
	repo_links += [' '.join(args.repo_link_and_SHA)]
walker.set_repo_links( repo_links)
walker.iterate_over_repos()
	

