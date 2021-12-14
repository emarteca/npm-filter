import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
import re
import json
import logging
import argparse
import time
import sys
sys.path.append("..")
from src import middlewares

logging.getLogger('scrapy').propagate = False

class NPMRepoSpider(scrapy.Spider):
	name = "npm-repos"
	
	def __init__(self, packages=None, good_repo_list_mode=None, *args, **kwargs):
		if packages is not None:
			self.packages = packages
		self.start_urls = ['https://www.npmjs.com/package/' + pkg for pkg in self.packages]
		self.pkg_repolink_pairs = []
		# dispatcher.connect(self.spider_closed, signals.spider_closed)
		self.good_repo_list_mode = good_repo_list_mode
		super(NPMRepoSpider, self).__init__(*args, **kwargs)

	def parse(self, response):
		cur_pkg = response.url[ len("https://www.npmjs.com/package/"):]
		# TODO should we handle specific response codes?
		# successful responses are those in the 200s
		# source: https://doc.scrapy.org/en/latest/topics/spider-middleware.html#module-scrapy.spidermiddlewares.httperror
		if response.status > 299 or response.status < 200:
			self.pkg_repolink_pairs += [(cur_pkg, "ERROR")]
		else:
			soup = BeautifulSoup(response.body, 'html.parser')
			script = soup.find('script', text=re.compile('window\.__context__'))
			json_text = re.search(r'^\s*window\.__context__\s*=\s*({.*?})\s*$',
			                      script.string, flags=re.DOTALL | re.MULTILINE).group(1)
			data = json.loads(json_text)
			repo_link = ""
			try:
				repo_link = data['context']['packument']['repository']
			except KeyError:
				repo_link = "ERROR"
			self.pkg_repolink_pairs += [(cur_pkg, repo_link)]
	def closed(self, reason):
      # second param is instance of spder about to be closed.
		if not self.good_repo_list_mode:
			print(self.pkg_repolink_pairs)
		else:
			good_repos = [rp[1] for rp in self.pkg_repolink_pairs if rp[1] != "ERROR" and rp[1] != ""]
			print("\n".join(good_repos))
	
process = CrawlerProcess(settings={
	"FEEDS": {
		"items.json": {"format": "json"},
	},
	"HTTPERROR_ALLOW_ALL": True,
	"RETRY_HTTP_CODES" : [429],
	# next couple settings are for beating the npm request rate limiter
	#"DOWNLOAD_DELAY": 0.75,    # 3/4 second delay
	"RETRY_TIMES": 6,
	#"CONCURRENT_REQUESTS_PER_DOMAIN" : 2,
 	"DOWNLOADER_MIDDLEWARES": {
 		"scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
 		"middlewares.TooManyRequestsRetryMiddleware": 543,
	}
})


argparser = argparse.ArgumentParser(description="Get repo link for packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='*', help="a package to get repo link for")
argparser.add_argument("--package_file", metavar="package_file", type=str, nargs='?', help="file with list of packages to get links for")
argparser.add_argument("--good_repo_list_mode", metavar="good_repo_list_mode", type=bool, nargs='?', help="if true, print only the repo links with no errors")
args = argparser.parse_args()

packages=[]
if args.packages:
	packages += args.packages
if args.package_file:
	with open(args.package_file) as f:
		packages += f.read().split("\n")

process.crawl(NPMRepoSpider, packages=packages, good_repo_list_mode=args.good_repo_list_mode)
process.start() # the script will block here until the crawling is finished
	

