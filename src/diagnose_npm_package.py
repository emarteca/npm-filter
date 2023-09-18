import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from bs4 import BeautifulSoup
import json
import re
import subprocess
import os
import logging
import argparse
from test_JS_repo_lib import *
import middlewares

logging.getLogger('scrapy').propagate = False

class NPMSpider(scrapy.Spider):
	name = "npm-pkgs"
	VERBOSE_MODE = False
	RM_AFTER_CLONING = False
	SCRIPTS_OVER_CODE = []
	CUSTOM_SETUP_SCRIPTS = []
	CUSTOM_LOCK_FILES = []
	QL_QUERIES = []

	DO_INSTALL = True
	INCLUDE_DEV_DEPS = False
	COMPUTE_DEP_LISTS = False
	TRACK_BUILD = True
	TRACK_TESTS = True
	TEST_VERBOSE_ALL_OUTPUT = False
	TEST_VERBOSE_OUTPUT_JSON = "verbose_test_report.json"
	TEST_COMMAND_REPEATS = 1

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
	
	def __init__(self, packages=None, config_file="", output_dir=".", *args, **kwargs):
		if packages is not None:
			self.packages = packages
		self.start_urls = ['https://www.npmjs.com/package/' + pkg for pkg in self.packages]
		self.set_up_config( config_file)
		self.output_dir = os.path.abspath(output_dir)
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
		self.IGNORED_SUBSTRINGS = cf_dict.get( "ignored_substrings", self.IGNORED_SUBSTRINGS)
		self.RM_AFTER_CLONING = cf_dict.get( "rm_after_cloning", self.RM_AFTER_CLONING)
		# script and query file location is relative to the config file
		self.SCRIPTS_OVER_CODE = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "scripts_over_code", self.SCRIPTS_OVER_CODE)]
		self.QL_QUERIES = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "QL_queries", self.QL_QUERIES)]
		self.CUSTOM_SETUP_SCRIPTS = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "custom_setup_scripts", self.CUSTOM_SETUP_SCRIPTS)]

		cf_dict = config_json.get( "dependencies", {})
		self.INCLUDE_DEV_DEPS = cf_dict.get("include_dev_deps", self.INCLUDE_DEV_DEPS)
		self.COMPUTE_DEP_LISTS = cf_dict.get("track_deps", self.COMPUTE_DEP_LISTS)

		cf_dict = config_json.get( "install", {})
		self.DO_INSTALL = cf_dict.get("do_install", self.DO_INSTALL)
		self.INSTALL_TIMEOUT = cf_dict.get("timeout", self.INSTALL_TIMEOUT)
		self.CUSTOM_LOCK_FILES = [ os.path.abspath(os.path.dirname(config_file if config_file else __file__)) + "/" + p 
											for p in cf_dict.get( "custom_lock_files", self.CUSTOM_LOCK_FILES)]

		cf_dict = config_json.get( "build", {})
		self.TRACK_BUILD = cf_dict.get("track_build", self.TRACK_BUILD)
		self.BUILD_TIMEOUT = cf_dict.get("timeout", self.BUILD_TIMEOUT)
		self.TRACKED_BUILD_COMMANDS = cf_dict.get("tracked_build_commands", self.TRACKED_BUILD_COMMANDS)

		cf_dict = config_json.get("test", {})
		self.TEST_TIMEOUT = cf_dict.get("timeout", self.TEST_TIMEOUT)
		self.TRACKED_TEST_COMMANDS = cf_dict.get("tracked_test_commands", self.TRACKED_TEST_COMMANDS)
		self.TRACK_TESTS = cf_dict.get("track_tests", self.TRACK_TESTS)
		self.TEST_COMMAND_REPEATS = cf_dict.get("test_command_repeats", self.TEST_COMMAND_REPEATS)
		test_verbose_config = cf_dict.get("test_verbose_all_output", {})
		self.TEST_VERBOSE_ALL_OUTPUT = test_verbose_config.get("do_verbose_tracking", self.TEST_VERBOSE_ALL_OUTPUT)
		self.TEST_VERBOSE_OUTPUT_JSON = test_verbose_config.get("verbose_json_output_file", self.TEST_VERBOSE_OUTPUT_JSON)

	def parse(self, response):
		# TODO should we handle specific response codes?
		# successful responses are those in the 200s
		# source: https://doc.scrapy.org/en/latest/topics/spider-middleware.html#module-scrapy.spidermiddlewares.httperror
		if response.status > 299 or response.status < 200:
			json_results = { "http_error_code": response.status, "message": "Could not analyze url: " + response.url }
			with open( response.url[ len("https://www.npmjs.com/package/"):] + '__results.json', 'w') as f:
				json.dump( json_results, f, indent=4)
			return
		package_name = self.parse_process(response.body)
		with open(self.output_dir + "/" + package_name + '__page_data.html', 'wb') as f:
			f.write(response.body)
		
	def parse_process( self, html_text):	
		soup = BeautifulSoup(html_text, 'html.parser')
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
		
		with open(self.output_dir + "/" + package_name + '__results.json', 'w') as f:
			json.dump( json_results, f, indent=4)
		return(package_name)

	def iterate_over_pkgs_from_files( self):
		for pkg_name in self.packages:
			with open(pkg_name + '__page_data.html', 'rb') as f:
				html_text = f.read()
			self.parse_process(html_text)

process = CrawlerProcess(settings={
	"FEEDS": {
		"items.json": {"format": "json"},
	},
	"HTTPERROR_ALLOW_ALL": True,
        "RETRY_HTTP_CODES" : [429],
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "middlewares.TooManyRequestsRetryMiddleware": 543,
        }
    })


argparser = argparse.ArgumentParser(description="Diagnose npm packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='+', help="a package to be diagnosed")
argparser.add_argument("--config", metavar="config_file", type=str, nargs='?', help="path to config file")
argparser.add_argument("--html", metavar="html_file", type=bool, nargs='?', help="read from existing html instead of scraping")
argparser.add_argument("--output_dir", metavar="output_dir", type=str, nargs='?', help="directory for results to be output to")
args = argparser.parse_args()

output_dir = args.output_dir if args.output_dir else "."

config = args.config if args.config else ""
html = args.html if args.html else False

if not args.html:
	process.crawl(NPMSpider, packages=args.packages, config_file=config, output_dir=output_dir)
	process.start() # the script will block here until the crawling is finished
else:
	# reading from a config file
	spider = NPMSpider(args.packages, config_file=config, output_dir=output_dir)
	spider.iterate_over_pkgs_from_files()
	

