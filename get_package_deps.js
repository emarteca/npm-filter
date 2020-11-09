const {directDependents} = require('dependent-packages');
const {argv} = require('yargs');
const fs = require('fs');

let package_name = argv.package;
if (!package_name) {
	console.log("Usage: node get_package_deps.js --package npm_package_name [--output_file output_file_name]");
	process.exit(1);
}

let deps_list = directDependents(package_name);

if (!argv.output_file) {
	console.log(directDependents(package_name));
} else {
	fs.writeFile( argv.output_file, deps_list.join("\n"), (err)=> {
		if(err) {
			console.log("Error printing to: " + argv.output_file);
			process.exit(1);
		}
		console.log("Done getting deps for: " + package_name);
	});
}
