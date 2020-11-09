import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess
# from pydispatch import dispatcher
from bs4 import BeautifulSoup
import re
import json
import logging
import argparse

logging.getLogger('scrapy').propagate = False

class NPMRepoSpider(scrapy.Spider):
	name = "npm-repos"
	
	def __init__(self, packages=None, *args, **kwargs):
		if packages is not None:
			self.packages = packages
		self.start_urls = ['https://www.npmjs.com/package/' + pkg for pkg in self.packages]
		self.pkg_repolink_pairs = []
		# dispatcher.connect(self.spider_closed, signals.spider_closed)
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
			repo_link = data['context']['packument']['repository']
			self.pkg_repolink_pairs += [(cur_pkg, repo_link)]
	def closed(self, reason):
      # second param is instance of spder about to be closed.
		print(self.pkg_repolink_pairs)
	
process = CrawlerProcess(settings={
	"FEEDS": {
		"items.json": {"format": "json"},
	},
	"HTTPERROR_ALLOW_ALL": True
})


argparser = argparse.ArgumentParser(description="Get repo link for packages")
argparser.add_argument("--packages", metavar="package", type=str, nargs='*', help="a package to get repo link for")
argparser.add_argument("--package_file", metavar="package_file", type=str, nargs='?', help="file with list of packages to get links for")
args = argparser.parse_args()

packages=[]
if args.packages:
	packages += args.packages
if args.package_file:
	with open(args.package_file) as f:
		packages += f.read().split("\n")

process.crawl(NPMRepoSpider, packages=packages)
process.start() # the script will block here until the crawling is finished
	

