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

def run_command( command):
	process = subprocess.Popen( command.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	return( error, output, process.returncode)

def run_installation( pkg_json):
	MANAGER = ""

	# if there is a yarn lock file use yarn
	# if there is a package-lock, use npm
	# if there is neither, try npm first, and if that fails use yarn
	if os.path.exists( "yarn.lock"):
		print("yarn detected -- installing using yarn")
		MANAGER = "yarn "
		error, output, retcode = run_command( "yarn")
	elif os.path.exists( "package-lock.json"):
		print("package-lock detected -- installing using npm")
		MANAGER = "npm run "
		error, output, retcode = run_command( "npm install")
	else:
		print( "No installer detected -- trying npm")
		MANAGER = "npm run "
		error, output, retcode = run_command( "npm install")
		if retcode != 0:
			print( "No installer detected -- tried npm, error, now trying yarn")
			print(error)
			MANAGER = "yarn "
			error, output, retcode = run_command( "yarn")
	return( (MANAGER, retcode))

def run_build( MANAGER, pkg_json):
	error = None
	return( error)

def run_tests( MANAGER, pkg_json):
	test_scripts = [t for t in pkg_json["scripts"].keys() if not t.find("test") == -1]
	print("Trying test commands: ") 
	print(test_scripts)
	for t in test_scripts:
		print("Running: " + MANAGER + t)
		error, output, retcode = run_command( MANAGER + t)
		print( output)
	return( retcode, [])

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
	(MANAGER, retcode) = run_installation( pkg_json)
	if retcode != 0:
		print("ERROR -- installation failed")
		process.exit(0)

	# now, proceed with the build
	retcode = run_build( MANAGER, pkg_json)

	# then, the testing
	(retcode, test_info) = run_tests( MANAGER, pkg_json)


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
