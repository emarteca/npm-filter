#!/bin/bash

cp -r ../src ../configs/default_filter_config.json .
docker build -t npm-filter .

rm -r src
rm default_filter_config.json
