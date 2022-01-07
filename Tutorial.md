## Tutorial: example walk-through
This is a simple tutorial giving an example walkthrough of npm-filter usage, one basic and one advanced.
We assume you have `docker` installed.

### Setup
```
git clone https://github.com/emarteca/npm-filter.git
cd npm-filter
```

### Docker build
```
docker build -t npm-filter .
```

### Usage example 1
Basic usage: analyze GitHub repo at specified commit SHA, with default configuration
```
./runDocker.sh python3 src/diagnose_github_repo.py --repo_link_and_SHA https://github.com/streamich/memfs 863f373185837141504c05ed19f7a253232e0905
```

Since this is using a specific commit SHA, the output should match exactly.
The terminal output should be:
```
Diagnosing: memfs --- from: https://github.com/streamich/memfs          
Cloning package repository                                              
Checking out specified commit: 863f373185837141504c05ed19f7a253232e0905 
Running: yarn test                                                      
Running: yarn test:coverage                                             
Running: yarn tslint                                                    
```

The output file should be in `npm_filter_docker_results/memfs__results.json`, and the contents of the file should be:
```
{
    "installation": {
        "installer_command": "yarn"
    },
    "build": {
        "build_script_list": [
            "build"
        ]
    },
    "testing": {
        "test": {
            "num_passing": 265,
            "num_failing": 0,
            "test_infras": [
                "jest"
            ],
            "timed_out": false
        },
        "test:coverage": {
            "num_passing": 265,
            "num_failing": 0,
            "test_infras": [
                "jest"
            ],
            "timed_out": false
        },
        "tslint": {
            "test_linters": [
                "tslint -- linter"
            ],
            "RUNS_NEW_USER_TESTS": false,
            "timed_out": false
        }
    },
    "metadata": {
        "repo_link": "https://github.com/streamich/memfs",
        "repo_commit_SHA": "863f373185837141504c05ed19f7a253232e0905"
    }
}

```


### Usage example 2
Advanced usage: Analyze the same GitHub repo as above, but with a user-specified configuration file, running a script and a CodeQL query. 
Also track the package dependencies including the `devDependencies`.

#### Custom script
In this example, we will make a simple custom script. 
This will just list all the files in the directory.
Open a file `docker_configs/ls.sh`, and give it the contents:
```
#!/bin/bash
ls
```
**Note** you might need `sudo` to make this file, if you aren't in your `docker` group, since `docker` will own this directory if the container has already been run.

Make it an executable:
```
chmod +x docker_configs/ls.sh
```

#### CodeQL query
In this example, we will make a simple CodeQL query to list all the `await` expressions and the files they appear in the package source code.
Open a file `docker_configs/await.ql` and give it the contents:
```
import javascript

from AwaitExpr ae
select ae, ae.getFile()
```

#### Custom configuration file
Now, we need a configuration file to tell npm-filter to run this custom script and query.
We only need to include the configuration fields that we're changing; all other settings not specified use their default values.
Open a file `docker_configs/my_config.json` and give it the contents:
```
{
        "dependencies": {
                "track_deps": true,
                "include_dev_deps": true
        },
        "meta_info": {
                "scripts_over_code": [ "ls.sh"],
                "QL_queries": [ "await.ql"]
        }
}

```

#### Running and output
Now, run npm-filter with the custom settings:
```
./runDocker.sh python3 src/diagnose_github_repo.py --repo_link_and_SHA https://github.com/streamich/memfs 863f373185837141504c05ed19f7a253232e0905 --config dock
er_configs/my_config.json
```

The terminal output should be:
```
Diagnosing: memfs --- from: https://github.com/streamich/memfs
Cloning package repository
Checking out specified commit: 863f373185837141504c05ed19f7a253232e0905
Getting dependencies
Running: yarn test
Running: yarn test:coverage
Running: yarn tslint
Running script over code: /home/npm-filter/docker_configs/ls.sh
Running QL query: /home/npm-filter/docker_configs/await.ql
```

The output file should be in `npm_filter_docker_results/memfs__results.json` again, and the contents of the file should be (with dependencies truncated for readability):
```
{                             
    "installation": {
        "installer_command": "yarn"
    },
    "dependencies": {
        "dep_list": [
            "is-descriptor",   
            "is-plain-obj",  
            "util-deprecate",
            "source-map-resolve",
            "duplexer3",
            "parse5",         
            "boxen",
            "protoduck",  
            "promise-inflight",
            "aws-sign2",     
            "is-regex",     
            "conventional-changelog-angular",
            "forever-agent",
            "signal-exit",  
            ...
            "gauge",          
            "extend",
            "lodash.ismatch"       
        ],
        "includes_dev_deps": true
    },               
    "build": {                 
        "build_script_list": [
            "build"          
        ]                        
    },                  
    "testing": {              
        "test": {   
            "num_passing": 265,
            "num_failing": 0,  
            "test_infras": [ 
                "jest"      
            ],                               
            "timed_out": false
        },                    
        "test:coverage": {
            "num_passing": 265,   
            "num_failing": 0,
            "test_infras": [      
                "jest"   
            ],                           
            "timed_out": false
        },           
        "tslint": {
            "test_linters": [
                "tslint -- linter"                
            ],         
            "RUNS_NEW_USER_TESTS": false,
            "timed_out": false
        }                       
    },                    
    "scripts_over_code": {                            
        "/home/npm-filter/docker_configs/ls.sh": {
            "output": "CHANGELOG.md\nCODE_OF_CONDUCT.md\nCONTRIBUTING.md\nLICENSE\nREADME.md\ncodecov.yml\ncoverage\ndemo\ndocs\nlib\nnode_modules\npackage.json\nprettier.config.js\nrenovate.json\nsrc\
ntsconfig.json\ntslint.json\nyarn.lock\n"                 
        }                                                            
    },                         
    "QL_queries": {       
        "/home/npm-filter/docker_configs/await.ql": {}
    },
    "metadata": {
        "repo_link": "https://github.com/streamich/memfs",
        "repo_commit_SHA": "863f373185837141504c05ed19f7a253232e0905"
    }
}
```

The output from running the CodeQL query should be in `npm_filter_docker_results/memfs__await__results.csv`, and the contents should be (truncated for readability):
```
"ae","col1"                                                                                
"await p ... ', 'r')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... close()","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... ', 'a')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... ('baz')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... close()","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... ', 'a')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... close()","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... ', 'a')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... (0o444)","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
...
"await p ... '/foo')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... '/bar')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... oo', 5)","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... '/foo')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... arture)","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ...  'bar')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ... ', 'w')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await p ...  'bar')","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
"await f ... close()","/home/npm-filter/TESTING_REPOS/memfs/src/__tests__/promises.test.ts"
```


