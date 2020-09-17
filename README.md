# npm-filter
Tool to find npm packages that meet certain criteria, or to determine metrics for specific packages.

Details Forthcoming...

## System Requirements
This program assumes you have the following installed:
* python3 (running as python), with bs4 and scrapy libraries
* git
* npm
* yarn
* node

## Usage
`python diagnose-npm-package.py --packages p1 [p2, ...] [--config config_file]`

## TODOs
Things to still get working:
* support for tracking lab and jasmine 
* timeout option
* scraping for particular characteristics (filter for num deps, num passing tests, no failing tests, etc)
