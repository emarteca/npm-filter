// get the build requirements for the project, if they're present
// these are:
// - npm version
// - node version
// - OS
//
// some notes:
// - devs can specify a range of engines (npm, node) that their project works on.
//   If a range is specified we just get one version in the valid range
// - if the project specifically doesn't work on linux, then we're bailing -- this 
//   only makes linux docker containers

// also this is in JS instead of python bc the python semver library is garbage

const semver = require('semver');
const subproc = require('child_process');
const fs = require('fs').promises;

// can specify OS version: https://docs.npmjs.com/cli/v9/configuring-npm/package-json#os
// can specify node/npm version: https://docs.npmjs.com/cli/v9/configuring-npm/package-json#engines
async function get_reqs_from_pkg_json(pkg_json) {
    let reqs = {}

    let engines = pkg_json["engines"] || {};
    // if not specified, "*" any version
    let npm_req = engines["npm"] || "*"; 
    let node_req = engines["node"] ||  "*";

    // if a range is specified, get a version in the valid range
    let { node_version, npm_version } = await get_versions_in_range(node_req, npm_req);
    reqs["node_version"] = node_version;
    reqs["npm_version"] = npm_version;


    oss = engines["os"] ||  [];
    // explicit versions and linux is not listed
    if (oss.length > 0 && oss.indexOf("linux") == -1)
        reqs["linux"] = false
    // explicitly excluding linux :'(
    else if (oss.indexOf("!linux") != -1)
        reqs["linux"] = false
    else
        reqs["linux"] = true

    return reqs 
}

const BANNED_VERSION_SUBSTRINGS = ["beta", "alpha", "pre"]

// using semver, let's get a version that matches our specs
async function get_versions_in_range(node_version, npm_version) {
    let node_npm_version_pairs = [];
    try {
        node_npm_version_pairs = await get_node_npm_version_pairs();
    } catch(e) {
        console.log("Error getting npm/node pairs -- proceeding blind: " + e);
    }
    
    // normal route: we have the data.
    // now just need to find a pair that matches
    if (node_npm_version_pairs.length > 0) {
        for (const pair of node_npm_version_pairs) {
            if (is_banned(pair["npm"]) || is_banned(pair["node"])) {
                continue;
            }
            if (semver.satisfies(pair["npm"], npm_version) && semver.satisfies(pair["node"], node_version)) {
                return { "node_version": pair["node"], "npm_version": pair["npm"] }
            }
        }
    }

    // if we get here we didn't return in the if above
    // we don't have the data: get the list of all node versions from nvm: `nvm ls-remote`
    // and all npm versions from npm itself: `npm view npm versions`
    // NOTE: node version takes precedence over the npm version bc it's more commonly specified, 
    // and because it's more important 
    if (node_version !== "*" ) {
        // then we care about the node version
        subproc.exec('nvm ls-remote', { shell: '/bin/bash'}, (err, stdout, stderr) => {
            let versions = stdout.split("\n").map(v => v.trim().split(" ")[0]); // strip formatting and any space-delimited labels (LTS, etc)
            for (vers of versions) {
                if (is_banned(vers)) {
                    continue;
                }
                if (semver.satisfies(vers, node_version)) {
                    return { "node_version": vers, "npm_version": "*" }
                }
            }
        })
    }

    // if we get here, then we didn't have the version pair data, and we also didn't care about the node version
    // so let's get an npm version
    if (npm_version !== "*") {
        // then we care about the npm version
        subproc.exec('npm view npm versions --json', { shell: '/bin/bash'}, (err, stdout, stderr) => {
            let versions = JSON.parse(stdout);
            for (vers of versions) {
                if (is_banned(vers)) {
                    continue;
                }
                if (semver.satisfies(vers, npm_version)) {
                    return { "node_version": "*", "npm_version": vers }
                }
            }
        })
    }
    
    // no matching pairs: we're flying blind folks
    return { "node_version": "*", "npm_version": "*" }
}

// versions of node and the versions of npm they are bundled with
// see: https://stackoverflow.com/questions/51238643/which-versions-of-npm-came-with-which-versions-of-node
// read this file in -- from it we can get all the valid versions of npm and node
// for fetch usage: https://stackoverflow.com/questions/2499567/how-to-make-a-json-call-to-an-url/2499647#2499647
const NODE_NPM_VERSIONS_URL = 'https://nodejs.org/dist/index.json';
async function get_node_npm_version_pairs() {
    let resp = await fetch(NODE_NPM_VERSIONS_URL);
    // look for errors:
    if (!resp.ok) {
        throw new Error("Uh oh: error reaching npm/node version pairs");
    }
    let all_data = await resp.json();
    let node_npm_pairs = []; 
    for (const vers_data of all_data) {
        let node_version = vers_data["version"];
        let npm_version = vers_data["npm"];
        // if both were in the version data
        if (node_version && npm_version)
            node_npm_pairs.push({node: node_version, npm: npm_version})
    }
    return node_npm_pairs;
}  

// check if a version is banned 
function is_banned(vers) {
    for (const banned of BANNED_VERSION_SUBSTRINGS) {
        if (vers.indexOf(banned) > -1) {
            return true;
        }
    }
    return false;
}

function print_as_bash_vars(reqs) {
    for ( key in reqs) {
        console.log("export " + key + "=" + reqs[key]);
    }
}
   
async function main(proj_dir) {
    let pkg_json = {};
    try {
        pkg_json = JSON.parse(await fs.readFile(proj_dir + "/package.json", 'utf8'));
    } catch(e) {
        console.error("Error, bailing out: " + proj_dir + " invalid directory, could not load package.json");
        process.exit();
    }
    // get the node and npm versions
    let reqs = await get_reqs_from_pkg_json(pkg_json);
    print_as_bash_vars(reqs);
}

if (process.argv.length != 3) {
    console.error("Usage: node get_rel_project_req.js path_to_project_dir")
    process.exit()
}

let proj_dir = process.argv[2];
main(proj_dir);
