#!/bin/bash

projRoot=$1
projName=$2
query=$3
outputDir="."

if [ $# == 4 ]; then
	outputDir=$4
fi

# if there is no QLDBs folder yet, create it
if [ ! -d "QLDBs" ]; then
	mkdir QLDBs
fi

# make the QL DB and upgrade it, if it doesnt already exist

if [ ! -d "QLDBs/$projName" ]; then
	#export LGTM_INDEX_FILTERS='include:/'
	codeql database create --language=javascript --source-root $projRoot QLDBs/$projName
	codeql database upgrade QLDBs/$projName
fi

# run the query
codeql query run --database QLDBs/${projName} --output=${projName}_tempOut.bqrs $query
codeql bqrs decode --format=csv ${projName}_tempOut.bqrs > $outputDir/${projName}__`basename $query .ql`__results.csv
rm ${projName}_tempOut.bqrs