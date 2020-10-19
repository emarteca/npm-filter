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

logging.getLogger('scrapy').propagate = False

class NPMSpider(scrapy.Spider):
	name = "npm-pkgs"
	VERBOSE_MODE = False
	RM_AFTER_CLONING = False
	SCRIPTS_OVER_CODE = []
	QL_QUERIES = []

	INCLUDE_DEV_DEPS = False
	COMPUTE_DEP_LISTS = False
	TRACK_TESTS = True

	TRACKED_TEST_COMMANDS = ["test", "unit", "cov", "ci", "integration", "lint", "travis", "e2e", "bench", 
							 "mocha", "jest", "ava", "tap", "jasmine"]
	IGNORED_COMMANDS = ["watch", "debug"]
	IGNORED_SUBSTRINGS = ["--watch", "nodemon"]
	TRACKED_BUILD_COMMANDS = ["build", "compile", "init"]

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
		self.IGNORED_SUBSTRINGS = cf_dict.get( "ignored_substrings", self.IGNORED_SUBSTRINGS)
		self.RM_AFTER_CLONING = cf_dict.get( "rm_after_cloning", self.RM_AFTER_CLONING)
		self.SCRIPTS_OVER_CODE = cf_dict.get( "scripts_over_code", self.SCRIPTS_OVER_CODE)
		self.QL_QUERIES = cf_dict.get( "QL_queries", self.QL_QUERIES)

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
		# TODO should we handle specific response codes?
		# successful responses are those in the 200s
		# source: https://doc.scrapy.org/en/latest/topics/spider-middleware.html#module-scrapy.spidermiddlewares.httperror
		if response.status > 299 or response.status < 200:
			json_results = { "http_error_code": response.status, "message": "Could not analyze url: " + response.url }
			with open( response.url[ len("https://www.npmjs.com/package/"):] + '__results.json', 'w') as f:
				json.dump( json_results, f, indent=4)
			return
		package_name = self.parse_process(response.body)
		with open(package_name + '__page_data.html', 'wb') as f:
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
		
		with open(package_name + '__results.json', 'w') as f:
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
	"HTTPERROR_ALLOW_ALL": True
})


argparser = argparse.ArgumentParser(description="Diagnose npm packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='+', help="a package to be diagnosed")
argparser.add_argument("--config", metavar="config_file", type=str, nargs='?', help="path to config file")
argparser.add_argument("--html", metavar="html_file", type=bool, nargs='?', help="read from existing html instead of scraping")
args = argparser.parse_args()

config = args.config if args.config else ""
html = args.html if args.html else False

if not args.html:
	process.crawl(NPMSpider, packages=args.packages, config_file=config)
	process.start() # the script will block here until the crawling is finished
else:
	# reading from a config file
	spider = NPMSpider(args.packages, config_file=config)
	spider.iterate_over_pkgs_from_files()
	

