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
* testing -- make sure it's robust and can deal with potential errors in running packages
* automated scraping for packages (instead of user-specified list)

## Data Analysis
* overall meta analysis: about number of tests in a package, percentage of totally untested packages, percentage of failing packages, etc.
* scraping for particular characteristics (filter for num deps, num passing tests, no failing tests, etc)
