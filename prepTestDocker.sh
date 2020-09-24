#!/bin/bash

cp *.py default_filter_config.json tests
cd tests
docker build -t npm-filter .
cd ..
