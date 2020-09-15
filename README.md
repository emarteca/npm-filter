# npm-filter
Tool to find npm packages that meet certain criteria, or to determine metrics for specific packages.

Details Forthcoming...

## System Requirements
This program assumes you have the following installed:
* python3 (running as python)
* git
* npm
* yarn
* node

## Usage
`python diagnose-npm-package.py --packages p1 [p2, ...] [--config config_file]`

## TODOs
Things to still get working:
* build!!!
* support for tracking other testing frameworks (right now just tracking jest and mocha)
* timeout option
* proper reporting, in json output file
* scraping for particular characteristics (filter for num deps, num passing tests, no failing tests, etc)
* config file support
