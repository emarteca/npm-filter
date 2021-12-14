#!/bin/bash

cp ../*.py ../configs/default_filter_config.json .
docker build -t npm-filter .
